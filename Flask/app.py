# importing the necessary dependencies
import numpy as np #used for numerical analysis
import pandas as pd # used for data manipulation
from flask import Flask, render_template, request
import pickle
import joblib

app = Flask(__name__) # initializing a flask app

# Load the model (trying both pickle/joblib depending on how it was saved)
try:
    model = pickle.load(open('HDI.pkl', 'rb')) #loading the model
except:
    model = joblib.load('hdi_model.pkl')

@app.route('/') # route to display the home page
def home():
    return render_template('home.html') #rendering the home page

@app.route('/Prediction', methods=['POST', 'GET'])
def prediction():
    return render_template('indexnew.html')

@app.route('/Home', methods=['POST', 'GET'])
def my_home():
    return render_template('home.html')

@app.route('/predict', methods=['POST']) # route to show the predictions in a web UI
def predict():
    #reading the inputs given by the user
    input_features = [float(x) for x in request.form.values()]
    features_value = [np.array(input_features)]
    
    # Updated to 'Region' to match the actual model trained in the notebook
    features_name = ['Region', 'Life expectancy', 'Mean years of schooling', 'Gross national income (GNI) per capita']
    
    df = pd.DataFrame(features_value, columns=features_name)
    
    # predictions using the loaded model file
    output = model.predict(df)
    
    # Format the output for rounding (handling array shape)
    if isinstance(output, np.ndarray) and len(output.shape) > 0:
        y_pred = round(output[0], 2)
    else:
        y_pred = round(output, 2)
        
    if(y_pred >= 0.3 and y_pred <= 0.4):
        return render_template("resultnew.html", prediction_text = 'Low HDI '+ str(y_pred))
    elif(y_pred >= 0.4 and y_pred <= 0.7):
        return render_template("resultnew.html", prediction_text = 'Medium HDI '+str(y_pred))
    elif(y_pred >= 0.7 and y_pred <= 0.8):
        return render_template("resultnew.html", prediction_text = 'High HDI '+str(y_pred))
    elif(y_pred >= 0.8 and y_pred <= 0.94):
        return render_template("resultnew.html", prediction_text = 'Very High HDI '+str(y_pred))
    else:
        return render_template("resultnew.html", prediction_text = 'The given values do not match the range of values')
        
    # showing the prediction results in a UI
    # return render_template('resultnew.html', prediction_text=output)

if __name__ == '__main__':
    # running the app
    app.run(debug=True, port=5000)
