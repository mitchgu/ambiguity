# Ambiguity

Ambiguity is a python package for personal accounting.

>"On the road from the City of Skepticism, I had to pass through the Valley of Ambiguity." - Adam Smith - Mezzacotta 2016

## Things it can do now
* Scrape monthly statements in all possible formats from:
	* MIT Federal Credit Union
	* Bank of America
* Input login credentials from stdin or Keepass databases

## Things it might do later
* Scrape from more places like
	* Paypal
	* Venmo
	* Amazon
* Import scraped statements in a variety of formats into a standardized, object-oriented YAML list of transactions for organization and annotation
* Be able to translate the YAML lists to beancount files

## Things it depends on
* Python 3, probably at least 3.5
* Chrome, [Chromedriver](https://sites.google.com/a/chromium.org/chromedriver/)
* All the dependencies in `setup.py`/`requirements.in`

## Usage
* Install the package
* Create a `settings.yaml` file based on `settings_example.yaml` wherever you want to organize your files. Edit the fields accordingly

### Pulling statements
* In the same directory, run `ambi-pull` to pull from all the accounts specified in the settings.
	* Alternately use the form `ambi-pull <path_to_settings_file>`

### Playing with the Chrome Webdriver
* Running `ambi-scd` will start a Chrome webdriver with the profile directory specified in the settings and drop into a python interpreter

This is handy for altering the chrome profile's print settings so your print-friendly statements will print to nice-looking pdfs.

Also handy for testing out scraping procedures in the interpreter.