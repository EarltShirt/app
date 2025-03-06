import sys
from PyQt5.QtWidgets import (QApplication, QInputDialog, QWidget, QFileDialog, QPushButton, QTextEdit, QLabel, QVBoxLayout, QMessageBox)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QDir


import pandas as pd
import numpy as np
import os
import csv
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
from io import StringIO

expected_columns = 22

def preprocess_csv(file_path):
    output = StringIO()
    with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        writer = csv.writer(output)
        for row in reader:
            if len(row) > expected_columns:
                row = row[:expected_columns]
            writer.writerow(row)
    output.seek(0)
    return output


def get_columns(df):
    columns = [column for column in df.columns]
    return columns

def get_lot_amount(df):
    return df[df['Lot Amount'] >= 1.00]

def get_deposits_vt(df):
    df_300_500 = df[((df[['Net Deposits', 'First Deposit']].max(axis=1) >= 300) & (df[['Net Deposits', 'First Deposit']].max(axis=1) < 500))]
    df_500_1000 = df[((df[['Net Deposits', 'First Deposit']].max(axis=1) >= 500) & (df[['Net Deposits', 'First Deposit']].max(axis=1) < 1000))]
    df_1000_2000 = df[((df[['Net Deposits', 'First Deposit']].max(axis=1) >= 1000) & (df[['Net Deposits', 'First Deposit']].max(axis=1) < 2000))]
    df_2000 = df[(df[['Net Deposits', 'First Deposit']].max(axis=1) >= 2000)]
    return df_300_500, df_500_1000, df_1000_2000, df_2000

def get_deposits_puprime(df):
    df_150_300 = df[((df[['Net Deposits', 'First Deposit']].max(axis=1) >= 150) & (df[['Net Deposits', 'First Deposit']].max(axis=1) < 300))]
    df_300_500 = df[((df[['Net Deposits', 'First Deposit']].max(axis=1) >= 300) & (df[['Net Deposits', 'First Deposit']].max(axis=1) < 500))]
    df_500_1000 = df[((df[['Net Deposits', 'First Deposit']].max(axis=1) >= 500) & (df[['Net Deposits', 'First Deposit']].max(axis=1) < 1000))]
    df_1000 = df[((df[['Net Deposits', 'First Deposit']].max(axis=1) >= 1000))]
    return df_150_300, df_300_500, df_500_1000, df_1000

class VTApp(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(800, 600)

        directory_name = "tmp_res"

        # Create the directory
        try:
            os.mkdir(directory_name)
            print(f"Directory '{directory_name}' created successfully.")
        except FileExistsError:
            os.rmdir(directory_name)
            os.mkdir(directory_name)
            print(f"Directory '{directory_name} successfully suppressed and created.")
        except PermissionError:
            print(f"Permission denied: Unable to create '{directory_name}'.")
        except Exception as e:
            print(f"An error occurred: {e}")

        self.tmp_res = "tmp_res"
        self.platform = None  # Le broker n'est pas encore sélectionné
        self.ano_button = None  # Le bouton d'anomalie sera ajouté dynamiquement

        # Layout principal
        self.layout = QVBoxLayout()

        # Bouton pour choisir un broker
        self.broker_button = QPushButton('Choisir un broker')
        self.broker_button.clicked.connect(self.ask_broker)
        self.layout.addWidget(self.broker_button)

        # Bouton d'upload de fichier
        self.load_button = QPushButton('Upload CSV / XLSX')
        self.load_button.clicked.connect(self.get_file)
        self.layout.addWidget(self.load_button)

        # Bouton de téléchargement des résultats
        self.results_button = QPushButton('Download results (zip)')
        self.results_button.clicked.connect(self.download_all)
        self.layout.addWidget(self.results_button)

        self.setLayout(self.layout)

    def ask_broker(self):
        # Fenêtre de dialogue avec des boutons pour sélectionner le broker
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Sélection du broker")
        msg_box.setText("Sur quel broker travaillez-vous ?")
        
        puprime_button = msg_box.addButton("Puprime", QMessageBox.AcceptRole)
        vt_button = msg_box.addButton("VT", QMessageBox.AcceptRole)
        
        msg_box.exec_()

        # Détecter le bouton cliqué
        if msg_box.clickedButton() == puprime_button:
            self.platform = "puprime"
        elif msg_box.clickedButton() == vt_button:
            self.platform = "vt"
        else:
            QMessageBox.warning(self, "Erreur", "Veuillez choisir un broker valide.")
            return

        self.setup_anomaly_button()

    def setup_anomaly_button(self):
        # Supprime le bouton précédent s'il existe
        if self.ano_button:
            self.layout.removeWidget(self.ano_button)
            self.ano_button.deleteLater()
            self.ano_button = None

        # Création du bouton correspondant au broker sélectionné
        if self.platform == "puprime":
            self.ano_button = QPushButton('Compute Anomalies Positives for Puprime')
            self.ano_button.clicked.connect(self.get_anomalies_puprime)
        elif self.platform == "vt":
            self.ano_button = QPushButton('Compute Anomalies Positives for VT')
            self.ano_button.clicked.connect(self.get_anomalies_vt)

        # Trouver l'index du bouton "Download results" pour insérer le nouveau bouton juste avant
        index_results_button = self.layout.indexOf(self.results_button)
        self.layout.insertWidget(index_results_button, self.ano_button)



    def get_file(self):
        self.file_name, _ = QFileDialog.getOpenFileName(self, 'Open CSV', r"C:\\Users\\ariel\\OneDrive\\Documents\\iCloudDrive\\iyas_app\\data", "CSV files (*.csv *.xlsx)")
        # self.labelImage.setPixmap(QPixmap(self.file_name))
        print('File Name : ', self.file_name)
        self.load_data()

    def download_all(self):
        '''
        asks the user for a path, then moves all the previously
        generated files to that location after comrpessing them
        '''
        return 0
    
    def load_data(self):
        if self.file_name.endswith('.csv'):
            cleaned_csv = preprocess_csv(self.file_name)
            self.df = pd.read_csv(cleaned_csv, sep=',')

        elif self.file_name.endswith('.xlsx') or self.file_name.endswith('.xls'):
            self.df = pd.read_excel(self.file_name)
        else:
            raise ValueError("Format de fichier non supporté. Veuillez utiliser un fichier CSV ou Excel.")

    def get_anomalies_vt(self):
        temp_df = get_lot_amount(self.df)
        df_300_500, df_500_1000, df_1000_2000, df_2000 = get_deposits_vt(temp_df)
        anomalies_list_pos = []  # List to store anomaly rows
        anomalies_list_neg = []  # List to store anomaly rows

        # Ici l'endroit où on vérifie si tu te fais niquer par le broker
        for index, row in df_300_500.iterrows():
            if row['Commission'] < 400:
                anomalies_list_pos.append(row)
        for index, row in df_500_1000.iterrows():
            if row['Commission'] < 700:
                anomalies_list_pos.append(row)
        for index, row in df_1000_2000.iterrows():
            if row['Commission'] < 1200:
                anomalies_list_pos.append(row)
        for index, row in df_2000.iterrows():
            if row['Commission'] < 1400:
                anomalies_list_pos.append(row)

        # Ici quand il te met un peu trop bien
        for index, row in df_300_500.iterrows():
            if row['Commission'] > 400:
                anomalies_list_neg.append(row)
        for index, row in df_500_1000.iterrows():
            if row['Commission'] > 700:
                anomalies_list_neg.append(row)
        for index, row in df_1000_2000.iterrows():
            if row['Commission'] > 1200:
                anomalies_list_neg.append(row)
        for index, row in df_2000.iterrows():
            if row['Commission'] > 1400:
                anomalies_list_neg.append(row)

        # Create a DataFrame from the list of anomaly rows
        df_anomalies_pos = pd.DataFrame(anomalies_list_pos)
        df_anomalies_neg = pd.DataFrame(anomalies_list_neg)

        csv_pos_filename = self.tmp_res + "\\anomalies_positives.csv"
        csv_neg_filename = self.tmp_res + "\\anomalies_negatives.csv"

        print(f'Saving data to {csv_neg_filename} / temp res : {self.tmp_res}')

        df_anomalies_pos.to_csv(csv_pos_filename, index=False)
        df_anomalies_neg.to_csv(csv_neg_filename, index=False)


    def get_anomalies_puprime(self):
        temp_df = get_lot_amount(self.df)
        df_150_300, df_300_500, df_500_1000, df_1000 = get_deposits_puprime(temp_df)
        anomalies_list_pos = []  # List to store anomaly rows
        anomalies_list_neg = []  # List to store anomaly rows

        # print(df_150_300)

        for index, row in df_150_300.iterrows():
            try:
                commission = float(row['Commission'])
                if commission < 150:
                    anomalies_list_pos.append(row)
            except ValueError:
                continue  # Ignore la ligne si la conversion échoue

        for index, row in df_300_500.iterrows():
            try:
                commission = float(row['Commission'])
                if commission < 400:
                    anomalies_list_pos.append(row)
            except ValueError:
                continue

        for index, row in df_500_1000.iterrows():
            try:
                commission = float(row['Commission'])
                if commission < 700:
                    anomalies_list_pos.append(row)
            except ValueError:
                continue

        for index, row in df_1000.iterrows():
            try:
                commission = float(row['Commission'])
                if commission < 1200:
                    anomalies_list_pos.append(row)
            except ValueError:
                continue

        # Ici quand il te met un peu trop bien
        for index, row in df_150_300.iterrows():
            try:
                commission = float(row['Commission'])
                if commission > 150:
                    anomalies_list_neg.append(row)
            except ValueError:
                continue

        for index, row in df_300_500.iterrows():
            try:
                commission = float(row['Commission'])
                if commission > 400:
                    anomalies_list_neg.append(row)
            except ValueError:
                continue

        for index, row in df_500_1000.iterrows():
            try:
                commission = float(row['Commission'])
                if commission > 700:
                    anomalies_list_neg.append(row)
            except ValueError:
                continue

        for index, row in df_1000.iterrows():
            try:
                commission = float(row['Commission'])
                if commission > 1200:
                    anomalies_list_neg.append(row)
            except ValueError:
                continue


        # for index, row in df_150_300.iterrows():
        #     if isinstance(row['Commission'], (int, float)) and row['Commission'] < 150:
        #         anomalies_list_pos.append(row)
        # for index, row in df_300_500.iterrows():
        #     if isinstance(row['Commission'], (int, float)) and row['Commission'] < 400:
        #         anomalies_list_pos.append(row)
        # for index, row in df_500_1000.iterrows():
        #     if isinstance(row['Commission'], (int, float)) and row['Commission'] < 700:
        #         anomalies_list_pos.append(row)
        # for index, row in df_1000.iterrows():
        #     if isinstance(row['Commission'], (int, float)) and row['Commission'] < 1200:
        #         anomalies_list_pos.append(row)

        # # Ici quand il te met un peu trop bien
        # for index, row in df_150_300.iterrows():
        #     if isinstance(row['Commission'], (int, float)) and row['Commission'] > 150:
        #         anomalies_list_neg.append(row)
        # for index, row in df_300_500.iterrows():
        #     if isinstance(row['Commission'], (int, float)) and row['Commission'] > 400:
        #         anomalies_list_neg.append(row)
        # for index, row in df_500_1000.iterrows():
        #     if isinstance(row['Commission'], (int, float)) and row['Commission'] > 700:
        #         anomalies_list_neg.append(row)
        # for index, row in df_1000.iterrows():
        #     if isinstance(row['Commission'], (int, float)) and row['Commission'] > 1200:
        #         anomalies_list_neg.append(row)


        # anomalies positives : le broker te doit de l'argent
        # anomalies negatives : tu dois de l'argent au broker
        df_anomalies_pos = pd.DataFrame(anomalies_list_pos)
        df_anomalies_neg = pd.DataFrame(anomalies_list_neg)

        csv_pos_filename = self.tmp_res + "\\anomalies_positives.csv"
        csv_neg_filename = self.tmp_res + "\\anomalies_negatives.csv"

        print(f'Saving data to {csv_neg_filename} / temp res : {self.tmp_res}')

        df_anomalies_pos.to_csv(csv_pos_filename, index=False)
        df_anomalies_neg.to_csv(csv_neg_filename, index=False)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    fileprocessor = VTApp()
    fileprocessor.show()

    sys.exit(app.exec_())