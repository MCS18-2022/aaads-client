# Automated Aggressive Action Detection System - Client



## Setup


### Prerequisites

To install the software client on your machine, your machine must have:

* A working installation of Python 3, at least 3.7.

* A locally installed media codec for .mp4 files, otherwise the annotated video will not play.


### Installation

Clone this repository to your local machine:
```bash
git clone <link>
```

To avoid polluting the global environment, it is suggested that you create a local virtual environment. Within the cloned repository:
```bash
python3 -m venv .
source bin/activate
```

Install the software dependencies:
```bash
pip install -r requirements.txt
```

To launch the client:
```bash
python3 client.py
```
