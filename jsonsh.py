import os
from re import L
import anytree
import argparse
import json

argparser = argparse.ArgumentParser("jsonsh", description="explore JSON objects in a shell-like environment")
argparser.add_argument("file", help="the JSON file to read from")

args = argparser.parse_args()
file: str = args.file


if os.path.exists(file):
	with open(file, 'r') as f:
		obj = json.load(f)
else:
	obj = {}

cwd = ""
current_obj = obj

class LSError(Exception): pass

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

def lsbase(args: list[str]) -> dict:
	from_top = args[0][0] == '/'
	
	temp_cwd = "" if from_top else cwd
	temp_obj = obj if from_top else current_obj

	for key in (x for x in args[0].split('/') if x):
		if key != "..":
			if key not in temp_obj.keys():
				raise LSError(f"error: ls: key '{key}' not found")

			if type(temp_obj[key]) != dict:
				raise LSError(f"error: ls: value at '{key}' is not an object")

			temp_cwd+=f"/{key}"

			temp_obj = temp_obj[key]
			continue

		temp_obj = obj

		for key in (x for x in temp_cwd.split('/')[:-1] if x):
			temp_obj = temp_obj[key]

		temp_cwd = ''.join(cwd.split('/')[:-1])

	return temp_obj, temp_cwd

def gettype(value) -> str:
	return {dict: "object", list: "array", int: "number", float: "number", str: "string"}[type(value)]

while 1:
	try: cmd = input(f"{cwd}> ")
	except KeyboardInterrupt: print("CTRL-C")
	try: command = cmd.split()[0]
	except IndexError: continue
	try: args = cmd.split()[1:]
	except IndexError: args = []

	if command == "cd":
		if not args:
			print("error: cd: expected at least one argument")
			continue

		from_top = args[0][0] == '/'

		cwd = "" if from_top else cwd
		current_obj = obj if from_top else current_obj

		for key in (x for x in args[0].split('/') if x):
			if key != "..":
				if key not in current_obj.keys():
					print(f"error: cd: key '{key}' not found")
					break

				if type(current_obj[key]) != dict:
					print(f"error: cd: value at '{key}' is not an object")
					break

				cwd+=f"/{key}"

				current_obj = current_obj[key]
				continue

			current_obj = obj

			for key in (x for x in cwd.split('/')[:-1] if x):
				current_obj = current_obj[key]

			cwd = ''.join(cwd.split('/')[:-1])
			
		continue

	if command == "ls":
		if not args:
			for key in current_obj.keys():
				print(f"{key} [{gettype(current_obj[key])}]")

			continue

		try: temp_obj, _ = lsbase(args)
		except LSError as e:
			print(e)
			continue

		for key in temp_obj.keys():
			print(f"{key} [{gettype(temp_obj[key])}]")

		continue

	if command == "get":
		if not args:
			print("error: get: expected at least one argument")
			continue

		key = args[0]
		idx = None
		if len(args) > 1:
			try: idx = int(args[1])
			except ValueError: 
				print("error: get: index is not int")
				continue

		if key not in current_obj.keys():
			print("error: get: key not found")
			continue
		
		if idx is not None:
			if type(current_obj[key]) not in (list, str):
				print("error: get: unable to index element")
				continue
			try: print(current_obj[key][idx])
			except IndexError: print("error: get: index out of range")
			
			continue

		print(current_obj[key])
		continue

	if command == "lsr":
		if not args:
			tree = recurse(cwd if cwd else '/', current_obj)
			
			print(render(tree))
			continue

		try: temp_obj, temp_cwd = lsbase(args)
		except LSError as e:
			print(e)
			continue


		tree = recurse(temp_cwd if temp_cwd else '/', temp_obj)

		print(render(tree))
		continue

	if command == "cde":
		if len(args) < 2:
			print("error: cde: expected at least two arguments")
			continue

		key = args[0]
		try: index = int(args[1])
		except ValueError:
			print("error: cde: index is not an int")
			continue

		if key not in current_obj.keys():
			print("error: cde: key not found")
			continue

		if type(current_obj[key]) is not list:
			print("error: cde: value must be an array")
			continue

		try: new_obj = current_obj[key][index]
		except IndexError:
			print("error: cde: index out of range")
			continue

		if type(new_obj) is not dict:
			print("error: cde: element at array index is not an object")
			continue


		cwd+=f"/{key}[{index}]"

		current_obj = new_obj
		continue

	if command == "clear":
		os.system("cls" if os.name == "nt" else "clear")
		continue

	if command == "help":
		print(
			"cd <directory>: changes the current object",
			"ls [directory]: lists all keys in an object",
			"get <key> [index]: gets a value from a key",
			"clear: clears the screen",
			"exit: saves and exits the document",
			sep='\n')
		
		continue

	if command == "exit":
		with open(file, 'w') as f:
			json.dump(obj, f)
		
		exit(0)

	print(f"error: jsonsh: command '{command}' not found")