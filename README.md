# Battery Manager

Battery Manager is a web application designed to manage and monitor battery systems. It includes a backend API built with Python and FastAPI, and a frontend built with modern JavaScript frameworks.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Development](#development)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## Features

- Optimize battery usage based on consumption prediction and electricity prices
- Create Growatt schedule
- Integrates with HA using Pyscript to control Growatt TLX inverter and APX battery
- Can be deployed as Google Cloud Run web server with React frontend showing optimization schedule and cost savings 

## Installation

### Prerequisites


### Clone the Repository

```sh
git clone https://github.com/johanzander/batterymanager.git
cd batterymanager

## Roadmap

### Features 
- Update algorithm to use existing SOH
- Add proper URL
- Add Home Assistant Add-On
- App proper documentation
- Contribute Home Assistant Growatt Custom Component
- Add Growatt Schedule view in frontent
- Add report view with monthly savings summary

### Bugs
- todays electricity prices do not change to tomorrows at midnight when running Cloud Run
- HA energy consumption sensor value not working, using fixed value for now

### Verification
- Hourly settings not set in pyscript.
- Use buy electricity prices in UI, not Nordpool

