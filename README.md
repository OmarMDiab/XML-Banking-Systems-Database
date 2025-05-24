# BaseX XML Banking System

This project is a simple banking application built on top of the BaseX XML database. It demonstrates how to manage banking data using XML technologies, including validation and querying. The app provides a user-friendly interface for interacting with the banking database.

## Features

- **XML Data Storage:** All banking data is stored in XML format.
- **XSD Schema Validation:** Ensures that all XML data conforms to a defined schema for data integrity.
- **Pre-populated Database:** Comes with sample banking data for immediate use.
- **Interactive Web App:** Built with Streamlit for easy querying and interaction.
- **Cross-platform:** Works on Windows and other platforms with Java and Python support.

## App Screenshots

### Secure DB Authentication

We Created a new user to the BaseX server

- username: **"Bank_Admin"**
- Passowrd: **"bankadmin"**, "this is a demo project"
- Authority: **"Admin"**

So, this Login is for basexserver not static streamlit check!
<img src="App%20Screenshots/DB%20Authentication%20and%20security.png" alt="Login Screen" width="80%"/>

![Dashboard](App%20Screenshots/dashboard.png)

### Some Advanced Queries

<img src="App%20Screenshots/Customer_Segementation.png" alt="Customer Segmentation"/>

**Description: -**
This function queries **users.xml** using XQuery to retrieve all customer UserIDs (<UserID> where <Role> is customer). For each user, it fetches their accounts (from another XML file) and sums the <Balance> values. Customers are then grouped into segments based on total balance thresholds.

<img src="App%20Screenshots/Transaction_Analysis.png" alt="Transaction Analysis"/>

**Description: -**
This function queries **transactions.xml** using XQuery to group <Transaction> elements by day, month, or year based on the <Date> field. It calculates the total number and sum of <Amount> values for each period, returning a time-based transaction volume report.

Follow the instructions below to set up and use the system.

## Prerequisites

Before you start, ensure you have the following installed:

- [Java Runtime Environment (JRE)](https://www.java.com/en/download/) version 8 or higher

## Contents

- `basex/`: The full BaseX program directory, including the database system and its necessary files.
- `banking db/`: A pre-populated banking database with sample data.

## Setup Instructions

### 1. Extract the ZIP File

Extract the contents of `Populated for user.zip` to a folder of your choice on your local machine.

### 2. Run BaseX

The extracted `basex` folder contains everything you need to run BaseX.

- **Windows**:
  1. Navigate to the `basex/bin/` folder.
  2. Double-click on `BaseXServer.bat` to start the BaseX server.
  3. Optionally, you can open `BaseX.bat` to launch the BaseX graphical user interface (GUI) for easier interaction.

### 3. Load the Database

Once BaseX is running, the banking database should already be populated and ready to use.

#### Install dependencies: -

- **Python 3.8+**
- And install the dependencies

```bash
pip install -r requirements.txt
```

#### Interact with the Database

You can query and interact with the database using our app :).

```bash
streamlit run app.py
```
