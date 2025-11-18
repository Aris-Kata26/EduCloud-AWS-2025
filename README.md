# EduCloud Project

## Overview
EduCloud is an educational platform designed to facilitate the management of classes and students through a user-friendly graphical interface. The application connects to a MySQL database and allows users to perform CRUD (Create, Read, Update, Delete) operations on student and class records. Additionally, the project includes pre-configured Amazon Machine Images (AMIs) for various operating systems, ready for educational use.

## Features
- User interface built with Tkinter for easy navigation and management.
- Integration with AWS for creating and managing EC2 instances.
- Database connectivity using pymysql for persistent data storage.
- Pre-configured AMIs for Ubuntu, Kali Linux, and Windows Server.

## Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   cd EduCloud
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage
To run the application, execute the following command:
```
python gui/main.py
```

## AMIs Documentation
For details on the golden AMIs created on AWS, refer to the `docs/amis.md` file. This includes the AMI IDs and descriptions of the pre-configured features for each AMI.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License.