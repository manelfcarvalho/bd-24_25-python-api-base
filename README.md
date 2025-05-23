# Databases - Practical Assignment

The code and resources available in this repository are to be used only within the scope of the _BD 2024-2025_ course of the Bachelor in Informatics Engineering.

This repository provides a base implementation of the endpoints for the Databases project.

The system must be made available through a REST API that allows the user to access the system using HTTP requests (when content is required, JSON must be used). The followingfigure represents a simplified view of the system to be developed. As it is possible to see, the user interacts with the web server through the exchange of REST request/response (using Postman) and in turn the web server interacts with the database server through an SQL interface (e.g., Psycopg in the case of Python).

<p align="center">
  <img src="rest_api-v1.png" />
</p>

_The contents of this repository do not replace the proper reading of the assignment description._

## [Python](python) REST API

To start this demo run the script [`python demo-api.py`](demo-api.py). This will launch a local web server with the coded endpoints. You can then make requests to the endpoints through HTTP (e.g., open your web browser and access http://localhost:8080/departments). To organize the interactions with the web server it is best to use an application; for this assignment you must use [`Postman`](https://www.postman.com/downloads/). Postman supports _collections_, which allows you to group requests (such as those that you will have to develop for the practical assignment). You can also import collections (such as the examples provided).

HTTP works as a request-response protocol. For this work, three main methods might be necessary:

- **GET**: used to request data from a resource
- **POST**: used to send data to create a resource
- **PUT**: used to send data to update a resource

In Postman you need to specify the type of the request when creating a new one. For POST/PUT requests, the data should be sent in the _body_ of the request, using the _raw_ format with _JSON_ as highlighted in the following screenshot. An example can also be found in the demo Postman collection made available.

<p align="center">
  <img src="postman_post.png" />
</p>

For most of the endpoints it will also be necessary to pass an authentication token. You can define the token for each request in either the _Authorization_ or _Headers_ tab in Postman (which can also be seen in the previous image). 

The REST API must be expanded to fulfil the functionalities/endpoints required for the practical assignment. **This demo already includes the definition of the various endpoints, including examples with the base data for each endpoint (in the Postman demo), as well as what structure/data is expected to be returned.** You must also develop the database to support that application, which must be created in the PostgreSQL database that the web server connects to.

## Overview of the Contents
- [`python`](python) - Source code of web application template in python. It has template endpoints for the different types of requests (i.e., GET, POST, PUT) and how to interact with a PostgreSQL database server. This can/should be used as basis for the endpoints required for the practical assignment.
- [`postman`](postman) - An example of a collection of requests exported from the Postman tool. This collection is to be imported in the [Postman application](https://www.postman.com/downloads/).


## Requirements

To execute this project it is required to have installed:

- `python 3.X`
  - `psycopg2/3` (**conda install psycopg2-binary**)
  - `flask` (**conda install flask**)
  - `jwt` (**pip install pyjwt**)

## Database Setup

To set up the database for this project, follow these steps:

1. Create the database (if not already created):
   ```bash
   createdb projeto
   ```

2. Create the database schema (tables and relationships):
   ```bash
   psql -U aulaspl -d projeto -f sql/schema.sql
   ```

3. Install the database triggers:
   ```bash
   psql -U aulaspl -d projeto -f sql/triggers.sql
   ```

The triggers implemented in this project are:

1. **trigger_update_mean**: Automatically updates a student's mean grade whenever a new grade is added or updated.
2. **trigger_payment_status**: Updates payment status to 'Paid' when fees are fully paid for both majors and extra activities.
3. **trigger_check_capacity**: Prevents student enrollment in a course when the maximum capacity is reached.

These triggers ensure data consistency and automate important business rules in the database.

## Support

If you find an issue or have questions regarding the demo feel free to contact me: [jrcampos@dei.uc.pt](mailto:jrcampos@dei.uc.pt)


## Authors

* BD 2024-2025 Team - https://dei.uc.pt/lei/
* University of Coimbra
