# Lisogo

List of goals.

This is a prototype of application made with Flask, Mongodb and Emberjs. I also
used bootstrap and copy-pasted from html5 boilerplate.

Currently, most of my work has been focused on writting an application
boilerplate and a simple Object Document Mapper (ODM) that you can browse in
`lisogo/model`. You can also have a look at the unit tests which should be
pretty straighforward to understand.

The ODM has now most of the features I want in order to start working on the
actual application code, this is what I'm going to do next.

I'd love to hear from people who would like to comment and give me feedback,
especially experienced pythonists.

## Licensing

Copyright 2012 Martin Richard, martiusweb.net.

tl;dr: GNU/GPLv2, don't use it if you want to make money with it, evil things
like kill kittens (The later is not a license statement, there is no usage
restriction, even if it's about killing pets or be a bad person).

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 2 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see <http://www.gnu.org/licenses/>.

## Installation

### Set up your environment

Dependencies you must install (and are not documented here) are the following:

  * python2 (I only test lisogo with Python 2.7)
  * mongodb

You shoud create a virtualenv:

    virtualenv venv -p `which python2`

The python executable you want to use depend of your system, but you must use
Python 2.

Now you can start the virtual environement by sourcing `venv/bin/activate`,
and install the dependencies:

    . venv/bin/activate
    pip install Flask blinker pymongo

We use bootstrap, available as a git submodule:

    git submodule init
    git submodule install

Please note that you will have to install bootstrap dependencies (including
less, jshint, recess, etc).

### Install lisogo

First things first, we need to configure the application. You will do this by
copying `lisogo/config.py.dist` into `lisogo/config.py` and edit the values you
want.

The file is supposed to be well documented.

You then must build the css stylesheet from the less files, located in
`frontend/less`. One can use the make rules to ease the process:

    make stylesheet

Test if lisogo is correctly set up by calling `run_lisogo.py`, open
`http://127.0.0.1:5000` in your favorite firefox flavor.

## Tests

You can run unit tests by calling `run_test.py`.

## Documentation

One should be able to generate code documentation using Sphinx, but I've tried
yet.

## A few notes about coding conventions

The code conventions I use are pretty standard, but may not follow the most
common practices in python. I'm sorry for this.

In model classes, I currently use getters and setters since I like to make
clear that these operations might be overloaded in the future. I guess it's not
really pythonist either. I comment getters and setters only if they do
something else than returning or setting a value (checks, side effects, signals
emitted...). But I may change my mind very soon.

Setters return `self`.

## TODO

A known limitation of the ODM of lisogo is that all model classes must be in
the same package, which is not suitable for bigger projects, and not really
flexible.

I will soon check my code with pychecker, some of the previous statements in
the coding conventions section will soon be outdated.
