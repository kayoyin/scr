# Signed coreference annotation interface
Based on https://github.com/neulab/interpkeywords/tree/master/annotation

## Dependencies

Set up your environment:

    pip install -r requirements.txt
    git clone https://github.com/mitsuhiko/flask-oauth
    cd flask-oauth
    python setup.py install

## Running

First, you must set up the database:

    python3 annotation_interface.py \
        -data DATA_DIR \
        --init-db


Next, you can run the interface either locally or remotely.

Locally at [http://127.0.0.1:5000/](http://127.0.0.1:5000/):

    python3 annotation_interface.py
    
Remotely by running the following on the server:

    python3 annotation_interface.py --server --port=8888
