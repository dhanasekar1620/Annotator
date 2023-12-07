from __future__ import print_function
from flask import Flask, render_template,request,redirect,session,send_file,url_for,Response
from werkzeug.utils import secure_filename
import os, os.path
import io,sys
import time
import json,fitz
import uuid
import pandas as pd
import numpy as np


logfile='log.txt'
def deleteFile(fileName):
    mypath = fileName
    for root, dirs, files in os.walk(mypath):
        for file in files:
            os.remove(os.path.join(root, file))
    else:
      print("The file does not exist")
      
app = Flask(__name__)
app.config['UPLOAD_DIRECTORY']='PDF_file/'
app.config['static']='static/completed_folder/'
app.config['nlp_json']='nlp_training_json/'
app.config['trainning_data_path']='trainingData_model/'
app.config['ALLOWED_EXTENSIONS']=['.json']
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


def extract_text(pdf_file_path):
    all_text = []
    doc = fitz.open(pdf_file_path)
    page_count = doc.page_count
    for page_num in range(page_count):
        text = doc[page_num].get_text()
        all_text.append(text.replace('\n',' '))
    doc.close()
    return all_text

@app.route('/')
def homepage():
    #wb = session.get('wb')
    #wb.Close()
    return render_template("index.html")

@app.route('/nlp_home')
def nlp_home():
    return render_template("nlp_home.html")

@app.route('/train_model_home')
def train_model_home():
    return render_template("model.html")

@app.route('/train_model', methods=['POST','GET'])
def train_model():
    import spacy
    # Configuration and training data paths
    config_path = 'config\config.cfg'
    if request.method=="POST":
        try:
            
            file = request.files['file']
            if file:
                trainning_data_path=os.path.join(app.config['trainning_data_path'],secure_filename(file.filename))
                
                # Load the configuration and initialize the empty model
                config = spacy.config.Config().from_str(open(config_path).read())
                nlp = spacy.blank(config['lang'])

                # Load training data
                examples = []
                with open(training_data_path, 'r') as f:
                    for line in f:
                        data = spacy.training.example_from_dict(nlp, line)
                        examples.append(data)

                # Train the model
                print(len(examples))
                optimizer = nlp.begin_training()
                for i in range(config['training']['n_iter']):
                    losses = {}
                    for example in examples:
                        nlp.update([example], drop=config['training']['dropout'], sgd=optimizer, losses=losses)
                    print(f"Iteration {i + 1} Loss: {losses}")

                # Save the trained model to a folder
                output_dir = 'saved_model//'
                nlp.to_disk(output_dir)

            if os.path.exists('saved_model//'):
                print('model_path',os.path.abspath('saved_model//'))
                return os.path.abspath('saved_model//')
            else:
                return "File not found", 404
        except Exception as e:
            exc_type, exc_obj, tb = sys.exc_info()
            lineno = tb.tb_lineno
            ob='\nLINE.NO-{} : {}'.format(lineno, exc_obj)
                
            with open(logfile,'a',encoding='utf-8') as fp:
                fp.writelines(ob)

@app.route('/upload_nlp_json', methods=['POST'])
def upload_nlp_json():
    if request.method=="POST":
        try:
            import spacy
            from spacy.tokens import DocBin
            from tqdm import tqdm
            from spacy.util import filter_spans
            file = request.files['file'] 
            # open the file and get the number of sheets
            extension=os.path.splitext(file.filename)[1].lower()
            if file:
                if extension not in app.config['ALLOWED_EXTENSIONS']:
                    return 'Use JSON File'
                nlp_json_file_path=os.path.join(app.config['nlp_json'],secure_filename(file.filename))
                file.save(nlp_json_file_path)

                with open(nlp_json_file_path, 'r') as f:
                    data = json.load(f)
                training_data = []
                for example in data:
                  temp_dict = {}
                  temp_dict['text'] = example['content']
                  temp_dict['entities'] = []
                  for annotation in example['annotations']:
                    start = annotation['start']
                    end = annotation['end']
                    label = annotation['tag_name'].upper()
                    temp_dict['entities'].append((start, end, label))
                  training_data.append(temp_dict)
                nlp = spacy.blank("en") # load a new spacy model
                doc_bin = DocBin() # create a DocBin object
                for training_example  in tqdm(training_data): 
                    text = training_example['text']
                    labels = training_example['entities']
                    doc = nlp.make_doc(text) 
                    ents = []
                    for start, end, label in labels:
                        span = doc.char_span(start, end, label=label, alignment_mode="contract")
                        if span is None:
                            print("Skipping entity")
                        else:
                            ents.append(span)
                    filtered_ents = filter_spans(ents)
                    doc.ents = filtered_ents 
                    doc_bin.add(doc)
                uuidName=str(uuid.uuid4())
                os.mkdir('training_data\\'+uuidName)
                training_data_path='training_data\\'+uuidName+'\\'+'training_data.spacy'
                doc_bin.to_disk(training_data_path)
            if os.path.exists(training_data_path):
                print('training_data_path',os.path.abspath(training_data_path))
                return send_file(os.path.abspath(training_data_path), as_attachment=True, mimetype='application/json')
            else:
                return "File not found", 404
        except Exception as e:
            exc_type, exc_obj, tb = sys.exc_info()
            lineno = tb.tb_lineno
            ob='\nLINE.NO-{} : {}'.format(lineno, exc_obj)
                
            with open(logfile,'a',encoding='utf-8') as fp:
                fp.writelines(ob)
                
@app.route('/ocr', methods=['POST'])
def ocr():
##    deleteFile("uploads")
##    deleteFile("PDF_file")
    #image_data = request.files['file']
    file = request.files['file']
    PDF_file_path=os.path.join(app.config['UPLOAD_DIRECTORY'],secure_filename(file.filename))
    file.save(PDF_file_path)
    filename=file.filename
    
    all_text=extract_text(PDF_file_path)

    session['pdf_path'] = PDF_file_path
    return render_template("annotator.html",all_text=all_text)

@app.route('/get_json', methods=['POST'])
def get_json():
    uuidName=str(uuid.uuid4())
    os.mkdir('json\\'+uuidName)

    if request.method == 'POST':        
        received_data = request.json
        print(received_data)
        PDF_file_path = session.get('pdf_path')
        all_text=extract_text(PDF_file_path)
        page=''
        new_list = []

        for index, text in enumerate(all_text, start=1):
            annotations = []
            for item in received_data:
                if item['page'] == index:
                    content = item['text']
                    tag_name = item['tag_name']
                    start = text.find(content)
                    end = start + len(content)
                    annotations.append({
                        "content": content,
                        "start": start,
                        "end": end,
                        "tag_name": tag_name
                    })

            new_item = {
                "id": str(index),
                "content": text,
                "annotations": annotations
            }
            new_list.append(new_item)

    json_src='json\\'+uuidName+'\\'+'train.json'
    #print('new_list',new_list)
    with open(json_src,'w') as file:
        json.dump(new_list, file, indent=4)

    while True:
        try:
            with open(json_src, 'rb') as f:
                break
        except FileNotFoundError:
            time.sleep(1)
    session['json_path'] = json_src
    if os.path.exists(json_src):
        print(os.path.abspath(json_src))
        return send_file(os.path.abspath(json_src), as_attachment=True, mimetype='application/json')
    else:
        return "File not found", 404




if __name__ == '__main__':
    app.run()
    
