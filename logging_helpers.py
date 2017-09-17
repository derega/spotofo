
import json

class Filter:
  def filter(self, record):
    if not 'data' in record.__dict__:
      record.__dict__['data'] = None
    record.__dict__['data'] = json.dumps(record.__dict__['data'], sort_keys=True, indent=2)
    return True

