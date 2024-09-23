from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.rest import ApiException
import datetime

class InfluxDBConnection:
    def __init__(self, config):
        try:
            self.influx_client = InfluxDBClient(url=config['InfluxDB']['INFLUXDB_URL'], 
                                                token=config['InfluxDB']['INFLUXDB_TOKEN'],
                                                org=config['InfluxDB']['INFLUXDB_ORG'])
            
            self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.influx_client.query_api()
            self.buckets_api = self.influx_client.buckets_api()

        except ApiException as e:
            print(f"Errore nella connessione a InfluxDB: {e}")
        except Exception as e:
            print(f"Errore imprevisto: {e}")

    def create_bucket(self, bucket_name):
        try:
            retention_rules = [{
                "type": "expire",
                "everySeconds": 0
            }]
            
            bucket = self.buckets_api.create_bucket(bucket_name=bucket_name,
                                                    retention_rules=retention_rules,
                                                    org=config['InfluxDB']['INFLUXDB_ORG'])
            
            print(f"Bucket '{bucket_name}' creato con retention infinita.")
        
        except Exception as e:
            print(f"Errore durante la creazione del bucket: {e}")
    
    def write_record(self, bucket, org, point):
        try:
            self.write_api.write(bucket=bucket, org=org, record=point)
            print(f"Record scritto con successo nel bucket {bucket}")
        except Exception as e:
            print(f"Errore nella scrittura su InfluxDB: {e}")


    def query_data(self, bucket, plate):
        try:
            query = f'''
            from(bucket: "{bucket}")
            |> range(start: 0) 
            |> filter(fn: (r) => r._measurement == "car_plates")
            |> filter(fn: (r) => r.plate == "AB123CD")
            |> filter(fn: (r) => r._field == "value")
            |> last()
            '''
            

            result = self.query_api.query(org=config['InfluxDB']['INFLUXDB_ORG'], query=query)
            
            if not result:
                print(f"No results in '{bucket}' for '{plate}'.")
            else:
                print(f"Time: {result[0].records[0].get_time()}, Value: {result[0].records[0].get_value()}")
        
        except Exception as e:
            print(f"Errore nella query su InfluxDB: {e}")

    def close_connection(self):
        self.influx_client.close()
        print("Connessione a InfluxDB chiusa.")

# Configurazione di esempio
config = {
    'InfluxDB': {
        'INFLUXDB_URL': 'http://localhost:8086',
        'INFLUXDB_TOKEN': 'W0bej85SwCIOXe72p7ifB6X1SHniR-cvziWf8KhSdoPckVHri0KDCNIH9P-SbfgiLH-qETj3O-SX3Wmchy-FlQ==',  # Inserisci qui il tuo token InfluxDB
        'INFLUXDB_ORG': 'unitn',
        'INFLUXDB_BUCKET': 'my_infinite_retention_bucket'
    }
}

# Inizializza la connessione
influx_connection = InfluxDBConnection(config)

# Crea un bucket
#influx_connection.create_bucket(bucket_name="my_infinite_retention_bucket")

# Dati da scrivere
point = (
    Point("car_plates")
    .tag("plate","AB123CD")
    .field("value", -1)
  )


# Scrivi il record
influx_connection.write_record(config['InfluxDB']['INFLUXDB_BUCKET'], 
                               config['InfluxDB']['INFLUXDB_ORG'],
                               point)

# Interroga i dati
influx_connection.query_data("my_infinite_retention_bucket","AB123CD")

# Chiudi la connessione
influx_connection.close_connection()
