import copy
import json

class ObjectSerializer(json.JSONEncoder):
	def default(self, obj):
		if type(obj) is JSONObject:
			return obj.__dict__
		
		return super().default(obj)

class LSError(Exception): pass
class JSONObject: # copied from `objverify`, don't want to have it as a dependency
	def __init__(self, proto: dict):
		for key, value in proto.items():
			if type(value) is dict:
				value = JSONObject(value)

			if type(value) is list:
				value = copy.deepcopy(value)
				for i, val in enumerate(value):
					if type(val) is dict: value[i] = JSONObject(val)

			self.__dict__[key] = value

	def __getitem__(self, item: str):
		return self.__dict__.get(item)

	def __repr__(self) -> str:
		return json.dumps(self.__dict__, cls=ObjectSerializer)