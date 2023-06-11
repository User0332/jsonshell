import os
import dill
import copy
import anytree
import argparse
import json

argparser = argparse.ArgumentParser("jsonsh", description="explore JSON objects in a shell-like environment")
argparser.add_argument("file", help="the JSON file to read from")
argparser.add_argument('-p', "--pretty-print", action="store_true", default=False, help="write the JSON prettily to the result file")

args = argparser.parse_args()
file: str = args.file
indent: bool = args.pretty_print

if os.path.exists(file):
	with open(file, 'r') as f:
		obj = json.load(f)
else:
	obj = {}

cwd = ""
current_obj = obj

LOADED = [('/', obj)]

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
		return json.dumps(self.__dict__)
	
def render(node: anytree.Node) -> str:
	res = ""
	for prefix, fill, node in anytree.RenderTree(node):
		res+=f"{prefix}{node.name}\n"

	return res

def recurse(name: str, obj: dict) -> anytree.Node:
	root = anytree.Node(name)

	for key in obj.keys():
		if type(obj[key]) is dict:
			node = recurse(f"{key} [{gettype(obj[key])}]", obj[key])
			node.parent = root
			continue

		anytree.Node(f"{key} [{gettype(obj[key])}]", parent=root)

	return root

def lsbase(args: list[str]) -> tuple[dict, str]:
	from_top = args[0][0] == '/'
	
	temp_cwd = "" if from_top else cwd
	temp_obj = obj if from_top else current_obj

	for key in (x for x in args[0].split('/') if x):
		if key != "..":
			if key not in temp_obj.keys():
				raise LSError(f"ls: error: key '{key}' not found")

			if type(temp_obj[key]) != dict:
				raise LSError(f"ls: error: value at '{key}' is not an object")

			temp_cwd+=f"/{key}"

			temp_obj = temp_obj[key]
			continue

		temp_obj = obj

		for key in (x for x in temp_cwd.split('/')[:-1] if x):
			temp_obj = temp_obj[key]

		temp_cwd = ''.join(cwd.split('/')[:-1])

	return temp_obj, temp_cwd

def exec_cd(directory: str):
	global cwd
	global current_obj

	from_top = directory[0] == '/'

	cwd = "" if from_top else cwd
	current_obj = obj if from_top else current_obj

	for key in (x for x in directory.split('/') if x):
		if key != "..":
			if key not in current_obj.keys():
				print(f"cd: error: key '{key}' not found")
				break

			if type(current_obj[key]) != dict:
				print(f"cd: error: value at '{key}' is not an object")
				break

			cwd+=f"/{key}"

			current_obj = current_obj[key]
			continue

		current_obj = obj

		for key in (x for x in cwd.split('/')[:-1] if x):
			current_obj = current_obj[key]

		cwd = ''.join(cwd.split('/')[:-1])
			

def gettype(value) -> str:
	return {dict: "object", list: "array", int: "number", float: "number", str: "string", bool: "boolean"}[type(value)]

cdparser = argparse.ArgumentParser("cd", description="change the current object/directory")
cdparser.add_argument("directory", type=str, help="The object/location to change directory to")

delparser = argparse.ArgumentParser("del", description="delete a key")
delparser.add_argument("key", type=str, help="The key to delete")
group = delparser.add_mutually_exclusive_group()
group.add_argument("-i", "--index", type=int, nargs='?', default=None, help="The index to remove from (if the key points to an array)")
group.add_argument("-v", "--value", type=str, nargs='?', default=None, help="The value to remove (if the key points to an array)")

lsparser = argparse.ArgumentParser("ls", description="list all keys in current object")
lsparser.add_argument("-r", "--recursive", action="store_true", default=False, help="print out all the keys of child objects too")
lsparser.add_argument("key", type=str, nargs='?', default='', help="The object from which to list all keys")

getparser = argparse.ArgumentParser("get", description="get a property value")
getparser.add_argument("key", type=str, help="The key to retrieve the value from")
getparser.add_argument("index", type=int, nargs='?', default=None, help="The index to grab the value from (if the selected key points to an iterable value)")

loadparser = argparse.ArgumentParser("load", description="load a new object as the current one")
loadparser.add_argument("key", type=str, help="The key to retrieve the object from")
loadparser.add_argument("index", type=int, nargs='?', default=None, help="The index to grab the object from (if the selected key points to a list of object)")

setparser = argparse.ArgumentParser("set", description="set a property value")
setparser.add_argument("key", type=str, help="The key to set the value at")
setparser.add_argument("-i", "--index", type=int, default=None, help="The index to set the value at (if the selected key points to a list)")
setparser.add_argument("value", type=str, help="The actual value to be set to the key")

insparser = argparse.ArgumentParser("ins", description="insert a value into an array")
insparser.add_argument("key", type=str, help="The key that points to the array")
insparser.add_argument("index", type=int, help="The index to set the value at")
insparser.add_argument("value", type=str, help="The value to be set")

resizeparser = argparse.ArgumentParser("resize", description="set the length of an array")
resizeparser.add_argument("key", type=str, help="The key that points to the target array")
resizeparser.add_argument("length", type=int, help="The new array length")

exitparser = argparse.ArgumentParser("exit", description="exit the shell")
exitparser.add_argument("--nosave", action="store_true", help="Do not save on exit")

lenparser = argparse.ArgumentParser("len", description="get the length of a property")
lenparser.add_argument("key", type=str, help="The key that points to the target value")

helpparser = argparse.ArgumentParser("help", description="help on commands")
helpparser.add_argument("cmd", type=str, nargs='?', default=None, help="Optional specific command")

pyserializeparser = argparse.ArgumentParser("pyserialze", description="serialize the current JSON object into a Python one and write it to the given file using `dill`")
pyserializeparser.add_argument("file", type=str, default=None, help="Filename to write to")

#just for help msg
unloadparser = argparse.ArgumentParser("unload", description="unload an object off of the object stack and return to the place you were before loading")

while 1:
	try: cmd = input(f"{cwd}> ")
	except KeyboardInterrupt: print("CTRL-C")
	try: command = cmd.split()[0]
	except IndexError: continue
	try: args = cmd.split()[1:]
	except IndexError: args = []

	if command == "cd":
		try: directory = cdparser.parse_args(args).directory
		except SystemExit: continue # make sure it doesn't exit

		exec_cd(directory)

		continue

	if command == "ls":
		try: lsargs = lsparser.parse_args(args)
		except SystemExit: continue # make sure it doesn't exit

		recursive, listkey = lsargs.recursive, lsargs.key	

		if recursive:
			if not listkey:
				tree = recurse(cwd if cwd else '/', current_obj)
				
				print(render(tree))
				continue

			try: temp_obj, temp_cwd = lsbase([listkey])
			except LSError as e:
				print(e)
				continue

			
			tree = recurse(temp_cwd if temp_cwd else '/', temp_obj)

			print(render(tree))
			continue

		if not listkey:
			for key in current_obj.keys():
				print(f"{key} [{gettype(current_obj[key])}]")

			continue

		try: temp_obj, _ = lsbase([listkey])
		except LSError as e:
			print(e)
			continue

		for key in temp_obj.keys():
			print(f"{key} [{gettype(temp_obj[key])}]")

		continue

	if command == "get":
		try: getargs = getparser.parse_args(args)
		except SystemExit: continue

		key, idx = getargs.key, getargs.index

		if key not in current_obj.keys():
			print("get: error: key not found")
			continue
		
		if idx is not None:
			if type(current_obj[key]) not in (list, str):
				print("get: error: unable to index element")
				continue
			try: print(json.dumps(current_obj[key][idx]))
			except IndexError: print("get: error: index out of range")
			
			continue

		print(json.dumps(current_obj[key]))
		continue

	if command == "set":
		try: setargs = setparser.parse_args(args)
		except SystemExit: continue

		key, idx, val = setargs.key, setargs.index, setargs.value
		
		if idx is not None:
			if type(current_obj.get(key)) is not list:
				print("set: error: element is not an array")
				continue

			try:
				current_obj[key][idx] = json.loads(val)
			except IndexError: print("set: error: index out of range")
			except json.decoder.JSONDecodeError: print("set: error: invalid value (could not parse)")
			
			continue

		try: current_obj[key] = json.loads(val)
		except json.decoder.JSONDecodeError: print("set: error: invalid value (could not parse)")

		continue

	if command == "ins":
		try: insargs = insparser.parse_args(args)
		except SystemExit: continue

		key, idx, val = insargs.key, insargs.index, insargs.value

		if key not in current_obj.keys():
			print("ins: error: key not found")
			continue

		if type(current_obj[key]) is not list:
			print("ins: error: element is not an array")
			continue

		try: current_obj[key].insert(idx, json.loads(val))
		except json.decoder.JSONDecodeError: print("ins: error: invalid value (could not parse)")
		
		continue

	if command == "len":
		try: key: str = lenparser.parse_args(args).key
		except SystemExit: continue

		if key not in current_obj.keys():
			print("len: error: key not found")
			continue

		if type(current_obj[key]) not in (list, str, dict):
			print("len: error: element does not have a length")
			continue

		if type(current_obj[key]) is dict:
			print(len(current_obj[key].keys()))
			continue

		print(len(current_obj[key]))
		continue

	if command == "resize":
		try: resizeargs = resizeparser.parse_args(args)
		except SystemExit: continue

		key, length = resizeargs.key, resizeargs.length

		if key not in current_obj.keys():
			print("resize: error: key not found")
			continue

		if type(current_obj[key]) is not list:
			print("resize: error: key does not point to an array")
			continue

		if length < len(current_obj[key]):
			current_obj[key] = current_obj[key][:length]
			continue

		current_obj[key]+=([None]*(length-len(current_obj[key])))
		
		continue

	if command == "del":
		try: delargs = delparser.parse_args(args)
		except SystemExit: continue

		key, idx, val = delargs.key, delargs.index, delargs.value

		if key not in current_obj.keys():
			print("del: error: key not found")
			continue

		if idx is not None:
			if type(current_obj[key]) is not list:
				print("del: error: element is not an array")
				continue
			try: current_obj[key].pop(idx)
			except IndexError: print("del: error: index out of range")

			continue

		if val is not None:
			if type(current_obj[key]) is not list:
				print("del: error: element is not an array")
				continue
			try: current_obj[key].remove(json.loads(val))
			except json.decoder.JSONDecodeError: print("del: error: invalid value (could not parse)")
			except ValueError: print(f"del: error: value not in '{key}'")

			continue	


		current_obj.pop(key)
		continue

	if command == "load":
		try: loadargs = loadparser.parse_args(args)
		except SystemExit: continue

		key, idx = loadargs.key, loadargs.index

		if key not in current_obj.keys():
			print("load: error: key not found")
			continue

		to_load = current_obj[key]
		
		if idx is not None:
			if type(to_load) is not list:
				print("load: error: element is not an array")
				continue
			try: to_load = to_load[idx]
			except IndexError:
				print("load: error: index out of range")
				continue
			
		if type(to_load) is not dict:
			print(f"load: error: {key}{f'[{idx}]' if idx is not None else ''} is not an object")
			continue

		LOADED.append((cwd, to_load))
		cwd = ""
		current_obj = to_load

		continue

	if command == "pyserialize":
		try: fname: str = pyserializeparser.parse_args(args).file
		except SystemExit: continue
		
		try:
			with open(fname, 'wb') as f:
				dill.dump(JSONObject(current_obj), f)
		except OSError as e: print(f"pyserialize: error: {e}")

		continue

	if command == "unload":
		# just for help msg
		try: unloadparser.parse_args(args)
		except SystemExit: continue

		if len(LOADED) == 1:
			print("unload: error: there are no objects to unload")
			continue

		cwd = LOADED.pop()[0]
		current_obj = LOADED[-1][1]

		if cwd: exec_cd(cwd)

		continue

	if command == "clear":
		os.system("cls" if os.name == "nt" else "clear")
		continue

	if command == "pwd":
		print(cwd if cwd else '/')
		continue

	if command == "help":
		try: cmd = helpparser.parse_args(args).cmd
		except SystemExit: continue
		
		if cmd is None:
			print(
				"cd", "ls", "set", "resize", "get",
				"clear", "help", "pwd", "exit", "load", "unload",
				"del", "ins", "save", "len", "pyserialize",
				sep='\n'
			)

			continue

		if f"{cmd}parser" in globals().keys():
			try: globals()[f"{cmd}parser"].parse_args(["-h"])
			except SystemExit: continue

		if cmd == "save":
			print("save - save and write the object to the file")
			continue

		if cmd == "pwd":
			print("pwd - print working directory")
			continue

		if cmd == "clear":
			print("clear - clear the screen")
			continue

		print(f"help: error: '{cmd}' is not a command!")

	if command == "exit":
		try: exitargs = exitparser.parse_args(args)
		except SystemExit: continue

		if not exitargs.nosave:
			with open(file, 'w') as f:
				json.dump(obj, f, indent='\t' if indent else None)
		
		exit(0)

	if command == "save":
		with open(file, 'w') as f:
			json.dump(obj, f, indent='\t' if indent else None)

		continue

	print(f"jsonsh: error: command '{command}' not found")