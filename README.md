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
- Parameterize battery parameters in frontend
- Parameterize electricity parameters (Nordpool area) in frontend
- Use buy electricity prices in UI, not Nordpool
- Add proper URL
- Add Home Assistant Add-On
- App proper documentation
- Contribute Home Assistant Growatt Custom Component
- Add Growatt Schedule view in frontent


### Bugs
- todays electricity prices do not change to tomorrows at midnight when running Cloud Run
- HA energy consumption sensor value not working, using fixed value for now

### Verification
- Hourly settings not set in pyscript.
- Integrate optimized algorithm.
- Use cookies to remember users settings
- Add historic electricity prices in UI
- Add today/tomorrow prices in UI

