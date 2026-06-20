# Huawei Solar Price Automation

A simple Python script I made to stop a solar plant from generating power when electricity prices on the market drop below zero (or a specific threshold). 

The script pulls prices from the ENTSO-E transparency platform every 15 minutes. If the current price is too low, it logs into the Huawei FusionSolar portal and limits the active power to 0%. When the price goes back up, it restores the power to 100%.

### Setup
You will need to add your own credentials in the code to make it work:
- ENTSO-E security token
- Huawei FusionSolar email and password
- Your specific plant code

*(Make sure not to commit your actual passwords if you fork this!)*

### Stuff used
- requests for handling the API calls and session cookies
- xml.etree.ElementTree because the ENTSO-E API returns XML instead of JSON
- time and datetime to sync the script with the 15-minute market intervals
