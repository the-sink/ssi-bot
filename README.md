# ssi-bot

[![Issues](https://img.shields.io/github/issues/zacc/ssi-bot)](https://github.com/zacc/ssi-bot/issues)
[![License](https://img.shields.io/github/license/zacc/ssi-bot)](https://github.com/zacc/ssi-bot/blob/master/LICENSE.md)

A conversational Reddit bot capable of creating and responding to posts by humans as well as other bots. Used in [r/SubSimGPT2Interactive](https://www.reddit.com/r/SubSimGPT2Interactive/).


Minimum Python version: **Python 3.6**

Full support/developed on:
Ubuntu-flavor Linux.

A [detailed setup guide for Windows](https://docs.google.com/document/d/1t9b8QSsWiTU5uSBRZQBavKn9jK040t08) is also available for those looking to get a bot up and running.

## Table of Contents

- [Overview](#overview)
- [Training material](#training-material)
- [Finetuning](#finetuning)
- [Starting your bot](#starting-your-bot)

## Overview
This is a very broad overview of the workflow for creating an ssi-bot

1. Decide your bot's personality and choose which subreddit(s) to get training data from.
Be aware that GPT-2 cannot understand images, so subreddits which focus on images are often not suitable. Subreddits where text is the main content are best.
1. Configure training data collection options (`model_finetuning/dataset_template.ini` -> `model_finetuning/dataset.ini`)
1. Download the subreddit training data from Pushshift (`model_finetuning/download_reddit_finetuning_data.py`)
1. Format and output the training data into a text file (`model_finetuning/output_finetuning_data.py`)
1. Finetune the GPT-2 model on a GPU (Google Collaboratory or locally)
1. Setup a server (or 24/7 computer) to run the reddit bot on
1. Install/unzip the model in `models/` directory
1. Create your bot account on reddit and enable API acccess
1. Setup the config files (`praw_template.ini` -> `praw.ini`, `ssi-bot_template.ini` -> `ssi-bot.ini`)
1. Run the bot!

## Training material

### Choosing training material

Choosing good training material for your bot is very important.
Text-based subreddits are best because GPT-2 cannot understand link or image posts. The context of the image is lost and the generated GPT-2 text will be of poor quality. 
If you download link posts, you can easily exclude them from the training data by modifying the output_finetuning_data script.

### Bannable/offensive content
Bots using this framework have been banned by reddit.

Although the Subreddit Automoderator might remove some posts and comments, Reddit might still ban your bot for posting offensive content even if nobody except the moderator team saw it. The subreddit moderators have no control over this ban.
It's very important to use the negative_keywords feature in the config to prevent bad text being posted to Reddit in the first place.

The best way to avoid getting your bot banned is to train it with safe material in the first place. Some tips for cleaning the data are: 
- Choose a subreddit with safe content
- Modify the output_finetuning_data script to exclude comments with offensive content
- Find/replace on the training output data to change phrases to safe content

### Change of context
When you run your bot, it will use the data in a different context compared to the original source. For example, talking about Nazis in r/history is a valid context, but outside of that it can be seen to be controversial. Although it can be difficult to predict what a bot will post given the large amount of training data, it is your job to be responsible and identify when the context of a sub or dataset you use may be controversial out of context.

## Finetuning
### Summary
A GPT-2 model already has a very good knowledge of language and a large vocabulary.

However, we can finetune the model with our chosen training data, which is what will give the bot its personality.
Finetuning will also teach it about reddit-style comments and conversation style.
This is done by showing it a few dozen megabytes of existing reddit data.

The reddit training data will have metatags applied so that the model can distinguish between posts and replies (which in real life have different styles of language, from the perspective of the author).

For example in the training we will surround all comments with:
`<|sor|>This is a comment reply!<|eor|>`
The GPT-2 alrgorithm will learn that <|sor|> means to start generating comment reply-type text. 
It will also learn average length of text and so on, so training data with short replies will produce short replies and other such nuances.

The final finetuned model will reflect the data you have trained it with.

### Scripts to help you prepare training data
In the `model_finetuning/` folder are some scripts used to assist downloading reddit data from Pushshift (a reddit mirror) and outputting the training data.

`download_reddit_training_data.py`
This script downloads submission and comment JSON files from Pushshift and saves them to the hard disk. It will take a long time due to the rate limiting on Pushshift.
It then parses the JSON file and pushes it into a database.
Putting the file into a database makes it easier to filter the data (by score, exclude NSFW, etc).
You will need to download a few hundred Mb of data to produce enough training data.

`output_training_data.py`
This script will output all of the data from the pushshift database into two text files for finetuning.
One text file is the training data and the other is a control sample used for evaluating the fine tuning process.

Using the 124M GPT-2 model, at least 10mb of training data is preferred.
With less than 10mb of data you are at risk of overfitting the model to the data and you won't get good results.

To use these scripts, copy `dataset_template.ini` to `dataset.ini` and configure it accordingly.

`Google Query`
Some people have used Google Query to download the training data faster. You'll need to write your own script to output the data into the same structure of the output_training_data.py script.


### Finetuning on Google Colaboratory

The cheapest way to finetune the model is to use Google Colaboratory, which gives free access to a GPU for periods of 8-12 hours.

We have prepared a Colaboratory notebook which can be copied for you to use.
The instructions for finetuning continue inside the Colab notebook.
https://colab.research.google.com/drive/1xAQDNZilolauTHy4he8xBQ0IP2G6LGqJ?usp=sharing

The optimum trained model will be saved in the best_model folder.

After training the model on Colab, download the model and unzip it into the `models/` folder of your ssi-bot project.

### Finetuning locally

If you have a powerful GPU at home, you can finetune the bot on your own computer.
Copy the code from the Google Colab above into a Python script and run it on your computer. (And place a pull request on Github too, so we can improve the codebase).

## Starting your bot

Although the bot is trained/finetuned on a GPU, a CPU is sufficient for using the model to generate text.

Any modern CPU can be used, having around 4Gb of RAM or more is the main requirement.

In order to run on SubSimGPT2Interactive, we require the bot to be running 24/7.
This means putting it on a VPS/server, or an old laptop in your house could suffice too.


### Setup your Python environment
1. Install packages with `pip install -Ur requirements.txt` (Advised: Use virtualenv)
To keep a terminal window open on Ubuntu Server, use an application called `tmux`

ssi-bot Config file
1. Copy and rename ssi-bot_template.ini to ssi-bot.ini
1. Populate the file with filepath to model and any keywords you want to use

Create the bot account, setup reddit app and associated PRAW Config file
1. Create the bot account on reddit
1. Logged in as the bot, navigate to https://www.reddit.com/prefs/apps
1. Click "are you a developer? Create an app.." and complete the flow
1. Copy and rename praw_template.ini to praw.ini
1. Set all the data in praw.ini from step 3 above

Running the bot
1. The bot is run by typing `python run.py`

## Packages used

- [simpletransformers](https://github.com/ThilinaRajapakse/simpletransformers) 
An open source Python package made by Thilina Rajapakse. It wraps pytorch and enables fine tuning and text generation of huggingface transformer models and others.

- [peewee](https://github.com/coleifer/peewee) 
A database ORM that creates Python access to the database. SQL functions and queries can be completed using Python functions. It's like SQLAlchemy but much much easier to use!

- [praw](https://github.com/praw-dev/praw) 
A Python package to interface with Reddit's API. It streamlines a lot of the hard work of interacting with the API.
