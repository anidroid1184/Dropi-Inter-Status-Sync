import time
import gspread
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from oauth2client.service_account import ServiceAccountCredentials
import logging
from datetime import datetime
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import sys
import io

# Cargar variables de entorno
load_dotenv()

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class InterrapidisimoTracker:
    def __init__(self):
        # Configurar Selenium (usando Chrome)
        options = webdriver.ChromeOptions()
        #options.add_argument("--headless=new")  # usa el nuevo modo headless de Chrome
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

        # Configuración de Google Sheets y Drive
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.file",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        self.client = gspread.authorize(creds)

        # Inicializar servicios de Google
        self.drive_service = build('drive', 'v3', credentials=creds)
        self.sheets_service = build('sheets', 'v4', credentials=creds)

        # Obtener configuración desde .env
        self.drive_folder_id = os.getenv('DRIVE_FOLDER_ID','1NFxV8NhmOnO8O1UmLNHH5HG8v3bOkjDA')
        self.spreadsheet_name = os.getenv('SPREADSHEET_NAME', 'seguimiento')

        # Abrir spreadsheet de seguimiento
        self.spreadsheet = self.client.open(self.spreadsheet_name)
    
    def get_latest_source_file(self):
        """Obtiene el archivo más reciente de la carpeta de Drive"""
        try:
            # Buscar archivos en la carpeta
            print(self.drive_folder_id)
            query = f"'{self.drive_folder_id}' in parents"
            results = self.drive_service.files().list(
                q=query,
                orderBy='createdTime desc',
                fields='files(id, name, createdTime)',
                includeItemsFromAllDrives=True,
                supportsAllDrives=True
            ).execute()
            print(results)

            files = results.get('files', [])
            if not files:
                logging.error("No se encontraron archivos en la carpeta especificada")
                return None

            # Devolver el archivo más reciente
            latest_file = files[0]
            logging.info(f"Archivo encontrado: {latest_file['name']} (ID: {latest_file['id']})")
            return latest_file

        except Exception as e:
            logging.error(f"Error al buscar archivos en Drive: {str(e)}")
            return None
    
    def read_source_data(self, file_id):
        import io
        import pandas as pd
        from googleapiclient.http import MediaIoBaseDownload

        try:
              # Descargar el archivo desde Drive
            request = self.drive_service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            fh.seek(0)

            # Leer el Excel con pandas
            df = pd.read_excel(fh, dtype={"NÚMERO GUIA": str})

            # Normalizar nombres de columnas
            df.columns = [c.strip().upper() for c in df.columns]

            # Filtrar registros válidos
            df = df[df["NÚMERO GUIA"].notna()]

            processed_data = []
            existing_guias = set()

            for _, row in df.iterrows():
                guia = str(row.get("NÚMERO GUIA", "")).strip()
                if not guia or guia in existing_guias:
                    continue
                existing_guias.add(guia)

                processed_data.append({
                    "ID DROPI": row.get("ID", ""),
                    "ID TRACKING": guia,
                    "STATUS DROPI": row.get("ESTATUS", "")
                })

            logging.info(f"Datos procesados: {len(processed_data)} registros válidos")
            return processed_data

        except Exception as e:
            logging.error(f"Error al leer archivo fuente: {e}")
            return []
        
    def update_tracking_sheet(self, data):
        """Actualiza la hoja de seguimiento con los nuevos datos"""
        try:
            sheet = self.spreadsheet.sheet1

            # Obtener guías existentes para evitar duplicados
            existing_records = sheet.get_all_records()
            existing_guias = {str(record.get('ID TRACKING', '')).strip() for record in existing_records if record.get('ID TRACKING')}

            # Preparar datos para añadir
            new_rows = []
            for item in data:
                if item['ID TRACKING'] not in existing_guias:
                    new_rows.append([
                        item['ID DROPI'],
                        item['ID TRACKING'],
                        item['STATUS DROPI'],
                        '',  # STATUS TRACKING (vacío inicialmente)
                        'FALSE'  # Alerta (inicialmente FALSE)
                    ])
                    existing_guias.add(item['ID TRACKING'])

            # Añadir nuevos registros
            if new_rows:
                # Obtener la última fila con datos
                all_values = sheet.get_all_values()
                last_row = len(all_values) + 1

                # Calcular rango final
                end_row = last_row + len(new_rows) - 1

                # Asegurar que haya suficientes filas
                max_rows = sheet.row_count
                if end_row > max_rows:
                 extra_rows = end_row - max_rows
                 logging.info(f"Añadiendo {extra_rows} filas adicionales para acomodar los datos")
                 sheet.add_rows(extra_rows)

                # Actualizar la hoja
                sheet.update(f'A{last_row}:E{end_row}', new_rows)
            else:
                logging.info("No hay nuevos registros para añadir")

            return len(new_rows)

        except Exception as e:
            logging.error(f"Error al actualizar hoja de seguimiento: {str(e)}")
            return 0
    
    def get_shipment_status(self, tracking_number):
        """Obtiene el estado del envío desde la web de Interrapidísimo"""
        try:
            # Guardar la pestaña principal
            main_window = self.driver.current_window_handle

            # Navegar a la página de seguimiento
            self.driver.get("https://interrapidisimo.com/sigue-tu-envio/")

            
            # Localizar y completar el campo de número de guía
            tracking_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "inputGuide"))
            )
            
            tracking_input.clear()
            tracking_input.send_keys(tracking_number)

            # Enviar la búsqueda con la tecla ENTER
            tracking_input.send_keys(Keys.ENTER)

            # Esperar a que se abra la nueva pestaña
            WebDriverWait(self.driver, 10).until(EC.number_of_windows_to_be(2))
            # Cambiar a la nueva pestaña
            new_window = [window for window in self.driver.window_handles if window != main_window][0]
            self.driver.switch_to.window(new_window)

            # Esperar a que cargue la información en la nueva pestaña
            time.sleep(3)

            # Intentar extraer el estado del envío
            status = "NO ENCONTRADO"
            try:
                # Buscar el estado en diferentes ubicaciones posibles
                possible_selectors = [
                    "//h2[contains(text(), 'envío')]/following-sibling::p",
                    "//div[contains(@class, 'estado')]",
                    "//p[contains(@class, 'status')]",
                    "//*[contains(text(), 'entregado')]",
                    "//*[contains(text(), 'transito')]",
                    "//*[contains(text(), 'tránsito')]",
                    "//*[contains(text(), 'devuelto')]",
                    "//*[contains(text(), 'ENVÍO PENDIENTE POR ADMITIR')]",
                    "//*[contains(text(), 'Viajando a tu destino')]",
                    "//*[contains(text(), 'Recibimos')]",
                    "//*[contains(text(), 'En Centro Logístico Origen')]"
                ]

                for selector in possible_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            text = element.text.strip()
                            print(text)
                            if text:  # Evitar textos muy largos
                                status = text
                                break
                        if status != "NO ENCONTRADO":
                            break
                    except:
                        continue

            except Exception as e:
                logging.error(f"Error al extraer estado: {str(e)}")

            # Cerrar la pestaña actual y volver a la principal
            self.driver.close()
            self.driver.switch_to.window(main_window)

            # Normalizar el estado
            status_lower = status.lower()
            if any(word in status_lower for word in ['entregado', 'entregada', 'entregar']):
                return "ENTREGADO"
            elif any(word in status_lower for word in ['camino', 'viajando a tu destino', 'centro', 'ruta', 'transito', 'tránsito', 'recibimos']):
                return "EN TRÁNSITO"
            elif any(word in status_lower for word in ['pendiente', 'recibido', 'origen', 'envío pendiente por admitir']):
                return "PENDIENTE"
            elif any(word in status_lower for word in ['devuelto', 'devolución', 'retorno a centro logístico lrigen']):
                return "DEVUELTO"
            elif any(word in status_lower for word in ['agencia', 'recoger']):
                return "EN AGENCIA"
            else:
                return status

        except Exception as e:
            logging.error(f"Error al obtener estado para {tracking_number}: {str(e)}")
            if len(self.driver.window_handles) > 1:
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
            return "ERROR"
    
    def create_differences_sheet(self, differences):
        """Crea una nueva hoja con los registros que tienen diferencias"""
        try:
            # Nombre de la hoja con timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            sheet_name = f"Diferencias_{timestamp}"

            # Crear nueva hoja
            new_sheet = self.spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)

            # Encabezados
            headers = ["ID TRACKING", "STATUS DROPI", "STATUS TRACKING", "FECHA VERIFICACIÓN"]
            new_sheet.update('A1:D1', [headers])

            # Datos
            data = []
            for diff in differences:
                data.append([diff['tracking_number'],
                    diff['internal_status'],
                    diff['web_status'],
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ])

            if data:
                new_sheet.update('A2:D{}'.format(len(data) + 1), data)

            logging.info(f"Hoja de diferencias creada: {sheet_name} con {len(differences)} registros")

        except Exception as e:
            logging.error(f"Error al crear hoja de diferencias: {str(e)}")
    
    def update_tracking_statuses(self):
        """Actualiza los estados de tracking en la hoja de seguimiento"""
        differences = []

        try:
            sheet = self.spreadsheet.sheet1
            records = sheet.get_all_records()

            headers = sheet.row_values(1)
            if "STATUS TRACKING" not in headers:
                sheet.update_cell(1, len(headers) + 1, "STATUS TRACKING")
            if "Alerta" not in headers:
                sheet.update_cell(1, len(headers) + 2, "Alerta")

            headers = sheet.row_values(1)
            tracking_col = headers.index("ID TRACKING") + 1
            status_col = headers.index("STATUS DROPI") + 1
            estado_web_col = headers.index("STATUS TRACKING") + 1 if "STATUS TRACKING" in headers else len(headers) + 1
            alerta_col = headers.index("Alerta") + 1 if "Alerta" in headers else len(headers) + 2
            #cont = 0
            #PARAMETRO DEL SCRIPT SI EL ANTERIOR FINALIZO CORRECTO PASARLE 2 (EMPIEZA DE LA PRIMERA FILA A RECORRER)
            #SI EL SCRIPT EN ALGUN MOMENTO FALLO Y SE NECESITA REINICIAR QUE NO SE REINICIE DEL PRINCIPIO SINO DE LA FILA QUE HIZO EL CRASHEO
            #REVISAR LOGS PARA VER QUE FILA FALLO (POR ID TRACKING)
            filaEmpezar = int(sys.argv[1])
            logging.info("Empezando por la fila {}".format(filaEmpezar))
            for i, record in enumerate(records, start=2):
                #if cont == 10:
                    #break
                #cont = cont + 1
                if i >= filaEmpezar:
                
                    tracking_number = str(record.get("ID TRACKING", "")).strip()
                    if tracking_number and tracking_number != "ID TRACKING":
                
                      internal_status = record.get("STATUS DROPI", "")
                      web_stat = record.get("STATUS TRACKING","")
                     
                      if ((internal_status.upper() == "DEVOLUCION" and web_stat.upper() == "DEVUELTO") or
                        (internal_status.upper() == "ENTREGADO" and web_stat.upper() == "ENTREGADO")):
                         logging.info("El registro {} tiene un estado final, no será consultado".format(tracking_number))
                      else:
                         logging.info("Consultando estado de idTracking: {}".format(tracking_number))
                         web_status = self.get_shipment_status(tracking_number)
                         logging.info("Web status encontrado: {}".format(web_status))

                        # Actualizar STATUS TRACKING
                         sheet.update_cell(i, estado_web_col, web_status)

                        # Verificar si hay diferencia
                         if internal_status.upper() != web_status.upper():
                            differences.append({
                               'tracking_number': tracking_number,
                              'internal_status': internal_status,
                              'web_status': web_status
                            })

                         # Configurar alerta
                         alerta = "FALSE"
                         if web_status.upper() == "ENTREGADO" and internal_status.upper() != "ENTREGADO":
                             alerta = "TRUE"

                         sheet.update_cell(i, alerta_col, alerta)
                         logging.info(f"Actualizado {tracking_number}: DROPI={internal_status}, WEB={web_status}, Alerta: {alerta}")
                         time.sleep(2)

            # Crear hoja de diferencias si hay registros diferentes
            if differences:
                self.create_differences_sheet(differences)
                logging.info(f"Se encontraron {len(differences)} registros con diferencias")
            else:
                logging.info("No se encontraron diferencias entre STATUS DROPI y STATUS TRACKING")
            logging.info("Proceso de actualización de estados completado")
            
        except Exception as e:
            logging.error(f"Error al actualizar estados de tracking: {str(e)}")
    
    def process_files(self):
        """Proceso principal: transfiere datos y actualiza estados"""
        # Paso 1: Obtener el archivo más reciente
        logging.info("Buscando archivo más reciente en Google Drive...")
        latest_file = self.get_latest_source_file()
        if not latest_file:
               return False
        # Paso 2: Leer y procesar datos del archivo fuente
        logging.info("Leyendo datos del archivo fuente...")
        source_data = self.read_source_data(latest_file['id'])
        if not source_data:
            logging.warning("No se encontraron datos válidos en el archivo fuente")
            return False

        #Paso 3: Actualizar hoja de seguimiento
        logging.info("Actualizando hoja de seguimiento...")
        new_records = self.update_tracking_sheet(source_data)
        logging.info(f"Se añadieron {new_records} nuevos registros")

        # Paso 4: Actualizar estados de tracking
        #logging.info("Actualizando estados de tracking...")
        self.update_tracking_statuses()

        
        logging.info("Proceso completado exitosamente")
        return True


    
    def close(self):
        """Cerrar el navegador"""
        self.driver.quit()

def main():
    tracker = InterrapidisimoTracker()
    try:
        success = tracker.process_files()
        if not success:
            logging.error("El proceso no se completó exitosamente")
    except Exception as e:
        logging.error(f"Error en la ejecución principal: {str(e)}")
    finally:
        tracker.close()

if __name__ == "__main__":
    main()