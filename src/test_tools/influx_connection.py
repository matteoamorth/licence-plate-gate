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
            print(f"Connection error: {e}")
        except Exception as e:
            print(f"Error: {e}")

    def write_record(self, bucket, org, point):
        try:
            self.write_api.write(bucket=bucket, org=org, record=point)
            print(f"Record scritto con successo nel bucket {bucket}")
        except Exception as e:
            print(f"Errore nella scrittura su InfluxDB: {e}")

########################################################################

# EDITABLE PART

# Configuration example
config = {
    'InfluxDB': {
        'INFLUXDB_URL': 'http://localhost:8086',
        'INFLUXDB_TOKEN': 'WUapt2nHMnrPO4QmmkD4xdVmZrPScXxGbVVuvoQ_2sWz-6aTpLhlV2grsdAU_T9n6E2KSS-cXwn79mCcTbufrw==',    # InfluxDB token to insert
        'INFLUXDB_ORG': 'unitn',    # InfluxDB organization
        'INFLUXDB_BUCKET': 'iot_project'
    }
}


# ADD PLATE PROFILE
plate = (
    Point("car_plates")
    .tag("plate","MN012OP") # custom plate
    .field("value", 1)      # 1 allowed plate, -1 disable plate
  )





# END OF EDITABLE PART 
########################################################################
influx_connection = InfluxDBConnection(config)
influx_connection.write_record(config['InfluxDB']['INFLUXDB_BUCKET'], 
                               config['InfluxDB']['INFLUXDB_ORG'],
                               plate)

