from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import WriteOptions
from influxdb_client.client.query_api import QueryApi
from influxdb_client.rest import ApiException

class InfluxDBConnection:
    def __init__(self, config):
        try:
            self.influx_client = InfluxDBClient(url=config['InfluxDB']['INFLUXDB_URL'], 
                                                token=config['InfluxDB']['INFLUXDB_TOKEN'],
                                                org='unitn')
            
            self.write_api = self.influx_client.write_api(write_options=WriteOptions(batch_size=500, 
                                                                                     flush_interval=10_000, 
                                                                                     jitter_interval=2_000, 
                                                                                     retry_interval=5_000))
            
            self.query_api = self.influx_client.query_api()

            test_query = 'buckets()'
            result = self.query_api.query(query=test_query)
            
            print("Connessione a InfluxDB riuscita. Buckets disponibili:")
            for table in result:
                for record in table.records:
                    print(f"Bucket: {record.values.get('name')}")
        
        except ApiException as e:
            print(f"Errore nella connessione a InfluxDB: {e}")
        except Exception as e:
            print(f"Errore imprevisto: {e}")
        
    def close_connection(self):
        self.influx_client.close()
        print("Connessione a InfluxDB chiusa.")

config = {
    'InfluxDB': {
        'INFLUXDB_URL': 'http://localhost:8086',
        'INFLUXDB_TOKEN': 'x'
    }
}


influx_connection = InfluxDBConnection(config)

influx_connection.close_connection()

