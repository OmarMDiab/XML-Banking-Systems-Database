# BaseX - Populated for User

This ZIP file contains the full BaseX program along with a pre-populated banking database. Follow the instructions below to set up and use the system.

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
