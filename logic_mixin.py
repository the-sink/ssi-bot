#!/usr/bin/env python3
import logging

from datetime import datetime

from praw.models import (Submission as praw_Submission, Comment as praw_Comment)


class LogicMixin():
	"""
	This mixin contains all the logic for tagging comments,
	and replying to posts.
	It is abstracted so that users can update this code on their fork,
	while taking updates on the main classes.
	"""

	def _get_reply_tag(self, praw_thing):
		"""
		Get the reply tag to use.
		The model will generate text after this reply tag.

		*This section is customisable for your own bot and how it has been finetuned*
		"""

		# It's just a straight reply
		return '<|sor|>'

	def _get_random_new_submission_tag(self):
		# Selftext only returned for now
		# while GPT-2 will generate link submissions, the URLs are usually 404s.
		# This function is named to futureproof that
		# return random.choice(['<|sols|><|sot|>', '<|soss|><|sot|>'])

		return '<|soss|><|sot|>'

	def _collate_tagged_comment_history(self, praw_thing, to_level=6):
		"""
		Loop backwards (upwards in reddit terms) from the praw_thing through the comment up x times,
		tagging the content text in the same way as the training data is
		The resulting string will be passed to the model to generate a reply to

		*This section is customisable for your own bot and how it has been finetuned*

		Each <|tag|> behaves as metadata so the model knows the general writing style of
		titles, replies and so forth.

		"""
		counter = 0
		prefix = ''
		loop_thing = praw_thing

		while loop_thing and counter < to_level:
			if isinstance(loop_thing, praw_Submission):

				# prepend the tagged text
				if loop_thing.is_self:
					# selftext submission
					tagged_text = f"<|soss|><|sot|>{loop_thing.title}<|eot|><|sost|>{loop_thing.selftext}<|eost|>"
				else:
					# it's a link submission
					tagged_text = f"<|sols|><|sot|>{loop_thing.title}<|eot|><|sol|>{loop_thing.selftext}<|eol|>"

				if len(tagged_text + prefix) > 1500:
					# If the prefix becomes too long, the model text generation will break
					# Break the while loop here and just return whatever prefix we have
					break

				prefix = tagged_text + prefix

				# can't go any higher than a submission, so break the loop
				break

			elif isinstance(loop_thing, praw_Comment):
				# just a normal <|sor|>
				tagged_text = f'<|sor|>{loop_thing.body}<|eor|>'

				if len(tagged_text + prefix) > 1500:
					# If the prefix becomes too long, the model text generation will break
					# Break the while loop here and just return whatever prefix we have
					break

				prefix = tagged_text + prefix

			loop_thing = loop_thing.parent()
			counter += 1

		if len(prefix) > 1500:
			# The model can handle 1024 tokens, but a token is not just one character.
			# Just truncate the long string to be safe and hope for the best :)
			return prefix[-1450:]

		return prefix

	def calculate_reply_probability(self, praw_thing):
		# Ths function contains all of the logic used for deciding whether to reply

		if not praw_thing.author:
			# If the praw_thing has been deleted the author will be None,
			# don't proceed to attempt a reply. Usually we will have downloaded
			# the praw_thing before it is deleted so this won't get hit often.
			return 0
		elif praw_thing.author.name.lower() == self._praw.user.me().name.lower():
			# The incoming praw object's author is the bot, so we won't reply
			return 0

		# merge the text content into a single variable so it's easier to work with
		thing_text_content = ''
		submission_link_flair_text = ''
		submission_created_utc = None

		if praw_thing.type == 'submission':
			# object is a submission that has title and selftext
			thing_text_content = f'{praw_thing.title} {praw_thing.selftext}'
			submission_link_flair_text = praw_thing.link_flair_text or ''
			submission_created_utc = datetime.utcfromtimestamp(praw_thing.created_utc)

		elif praw_thing.type == 'comment':
			# otherwise it's a comment
			thing_text_content = praw_thing.body
			# navigate to the parent submission to get the link_flair_text
			submission_link_flair_text = praw_thing.submission.link_flair_text or ''
			submission_created_utc = datetime.utcfromtimestamp(praw_thing.submission.created_utc)

		# second most important thing is to check for a negative keyword
		# calculate whether negative keywords are in the text and return 0
		if len(self._negative_keyword_matches(thing_text_content)) > 0:
			# The title or selftext/body contains negative keyword matches
			# and we will avoid engaging with negative content
			return 0

		# if the submission is flaired as a subreddit announcement,
		# do not reply so as to not spam the sub
		if submission_link_flair_text.lower() in ['announcement']:
			return 0

		# if the bot is mentioned, or its username is in the thing_text_content, reply 100%
		if praw_thing.type == 'username_mention' or self._praw.user.me().name.lower() in thing_text_content.lower():
			return 1

		if praw_thing.type == 'comment':
			# Find the depth of the comment
			if self._find_depth_of_comment(praw_thing) > 9:
				# don't reply to comments at > 9, to stop bots replying forever
				# and also to keep the bot's comments high up and visible
				return 0

		# From here we will start to calculate the probability cumulatively
		# Adjusting the weights here will change how frequently the bot will post
		# Try not to spam the sub too much and let other bots and humans have space to post
		base_probability = 0

		# Check the flair and username to see if the author might be a bot
		# 'Verified GPT-2 Bot' is only valid on r/subsimgpt2interactive
		if 'verified gpt-2 bot' in (praw_thing.author_flair_text or '').lower()\
			or any(praw_thing.author.name.lower().endswith(i) for i in ['ssi', 'bot', 'gpt2']):

			base_probability += -0.1
		else:
			# assume humanoid if author metadata doesn't meet the criteria for a bot
			base_probability += 0.3

		if len(self._positive_keyword_matches(thing_text_content)) > 0:
			# A positive keyword was found, increase probability of replying
			base_probability += 0.3

		if praw_thing.type == 'submission':
			# it's a brand new submission and the bot can
			# comment at the top level and get some exposure..
			base_probability += 0.4

		if praw_thing.type == 'comment':
			if praw_thing.parent().author == self._praw.user.me().name:
				# the post prior to this is by the bot
				base_probability += 0.1

			if any(kw.lower() in praw_thing.body.lower() for kw in ['?', ' you']):
				# any interrogative terms in the comment,
				# an increased reply probability
				base_probability += 0.3

			if praw_thing.submission.author == self._praw.user.me().name:
				# the submission is by the author, and favor that
				base_probability += 0.1

		reply_probability = min(base_probability, 1)

		# work out the age of submission in hours
		age_of_submission = (datetime.utcnow() - submission_created_utc).total_seconds() / 3600
		# calculate rate of decay over 48 hours
		rate_of_decay = max(0, 1 - (age_of_submission / 48))
		# multiply the rate of decay by the reply probability
		return reply_probability * rate_of_decay

	def extract_reply_from_generated_text(self, prompt, generated_text, truncate):

		# remove any cruft
		generated_text = generated_text.replace('&amp;#x200B;\n', '')

		# find the first instance of the end-of-comment tag, starting from the end of the prompt
		index_of_truncate = generated_text.find(truncate, len(prompt))

		if index_of_truncate == -1:
			# the original truncate tag couldn't be found,
			# but we'll still try and truncate the string at the last line break (end of paragraph)
			# so that the text still looks clean.
			index_of_truncate = generated_text.rfind("\\n")
		if index_of_truncate == -1:
			# in case trained model do not output tags and put lot !!!!! at the end,
			# This change allows this messages without need of end tags
			index_of_truncate = generated_text.find("!!!!")

		if index_of_truncate == -1:
			# still nothing could be found so just skip this one
			# if this is hit often, increase the length of the generated text
			logging.info("Truncate string not found")
			return {}

		# extract the text from between the prompt and the truncate point
		reply_body = generated_text[len(prompt):index_of_truncate]
		if reply_body:
			return {'body': reply_body}

		# Return nothing
		return {}

	def extract_submission_text_from_generated_text(self, prompt, generated_text):

		# remove any cruft
		generated_text = generated_text.replace('&amp;#x200B;\n', '')

		title_start_tag = '<|sot|>'
		title_end_tag = '<|eot|>'

		idx_title_start = generated_text.find(title_start_tag)
		idx_title_end = generated_text.find(title_end_tag)

		if idx_title_start == -1 or idx_title_end == -1:
			# There must be at least a complete title to make a submission
			return {}

		if generated_text.startswith('<|sols|>'):
			submission_type = 'url'
			maintext_start_tag = '<|sol|>'
			maintext_end_tag = '<|eol|>'
		elif generated_text.startswith('<|soss|>'):
			submission_type = 'selftext'
			maintext_start_tag = '<|sost|>'
			maintext_end_tag = '<|eost|>'

		# Find the start and end tags of the main text, starting from the end of the title
		idx_maintext_start = generated_text.find(maintext_start_tag, idx_title_end)
		idx_maintext_end = generated_text.find(maintext_end_tag, idx_title_end)

		if idx_maintext_start != (idx_title_end + len(title_end_tag)):
			# check that the main text immediately follows the title end
			return {}

		if idx_maintext_start == -1 or idx_maintext_end == -1:
			# There must be a complete body (link or submission)
			return {}

		title = generated_text[idx_title_start + len(title_start_tag):idx_title_end]

		if not (0 < len(title) < 300):
			# Validate the title length is within reddit's range
			return {}

		maintext = generated_text[idx_maintext_start + len(maintext_start_tag):idx_maintext_end]

		return {'title': title, submission_type: maintext}
