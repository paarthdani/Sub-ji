# Sub-ji

Sub-ji is a REST service which has the facility to add a user and get a subscription from a pre-defined plan. 
On addition of a new plan this service will check if its an uprade or downgrade of the plan and debit/credit the amount accorndingly
We can also view the user and the details about the active subscription and all subscription by the user.

To run this application 
- make sure you have docker installed on the system
- Run the command - docker-compose up

This entire application is in a docker container so by running the above command all required dependency will be downloaded and will be ready to run.
It will start listening at port - 19093
