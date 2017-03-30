# This is a collection of scripts that will allow manipulation of CAMI profiling files
# TO DO: Add unifrac with flow (after I fix it in the EMDUnifrac repository)
import sys
import copy
import os


class Profile(object):
	def __init__(self, input_file_name=None):
		# Initialize file name (if appropriate)
		self.input_file_name = input_file_name
		self._data = dict()
		# Stick in the root node just to make sure everything is consistent
		self._data["-1"] = dict()
		self._data["-1"]["rank"] = None
		self._data["-1"]["tax_path"] = list()
		self._data["-1"]["tax_path_sn"] = list()
		self._data["-1"]["abundance"] = 0
		self._data["-1"]["descendants"] = list()
		self._data["-1"]["branch_length"] = 0
		self._header = list()
		self._tax_id_pos = None
		self._rank_pos = None
		self._tax_path_pos = None
		self._tax_path_sn_pos = None
		self._abundance_pos = None
		self._eps = .0000000000000001  # This is to act like zero, ignore any lines with abundance below this quantity

		if self.input_file_name:
			if not os.path.exists(self.input_file_name):
				print("Input file %s does not exist" % self.input_file_name)
				raise Exception
			else:
				self.parse_file()

	def parse_file(self):
		input_file_name = self.input_file_name
		_data = self._data
		_header = self._header
		with open(input_file_name, 'r') as read_handler:
			for line in read_handler:
				line = line.rstrip()
				if len(line) == 0:
					continue  # skip blank lines
				if line[0] == '@' and line[1] == '@':
					headers = line.strip().split()
					for header_iter in range(len(headers)):
						header = headers[header_iter]
						header = header.replace('@', '')
						if header == 'TAXID':
							tax_id_pos = header_iter
							self._tax_id_pos = tax_id_pos
						elif header == 'RANK':
							rank_pos = header_iter
							self._rank_pos = rank_pos
						elif header == 'TAXPATH':
							tax_path_pos = header_iter
							self._tax_path_pos = tax_path_pos
						elif header == 'TAXPATHSN' or header == "TAXPATH_SN":
							tax_path_sn_pos = header_iter
							self._tax_path_sn_pos = tax_path_sn_pos
						elif header == 'PERCENTAGE':
							abundance_pos = header_iter
							self._abundance_pos = abundance_pos
				if line[0] in ['@', '#']:
					_header.append(line)  # store data and move on
					continue
				if not all([isinstance(x, int) for x in [tax_id_pos, tax_path_pos, abundance_pos]]):
					print("Appears the headers TAXID, TAXPATH, and PERCENTAGE are missing from the header (should start with line @@)")
					sys.exit(2)
				temp_split = line.split('\t')
				tax_id = temp_split[tax_id_pos].strip()
				tax_path = temp_split[tax_path_pos].strip().split("|")  # this will be a list, join up late
				abundance = float(temp_split[abundance_pos].strip())
				if isinstance(rank_pos, int):  # might not be present
					rank = temp_split[rank_pos].strip()
				if isinstance(tax_path_sn_pos, int):  # might not be present
					tax_path_sn = temp_split[tax_path_sn_pos].strip().split("|")  # this will be a list, join up later
				if tax_id in _data:  # If this tax_id is already present, add the abundance. NOT CHECKING FOR CONSISTENCY WITH PATH
					_data[tax_id]["abundance"] += abundance
					_data[tax_id]["tax_path"] = tax_path
					if isinstance(rank_pos, int):  # might not be present
						_data[tax_id]["rank"] = rank
					if isinstance(tax_path_sn_pos, int):  # might not be present
						_data[tax_id]["tax_path_sn"] = tax_path_sn
					# Find the ancestor
					if len(tax_path) <= 1:
						_data[tax_id]["ancestor"] = "-1"  # no ancestor, it's a root
						_data[tax_id]["branch_length"] = 1
						ancestor = "-1"
					else:
						ancestor = tax_path[-2]
						_data[tax_id]["branch_length"] = 1
						i = -3
						while ancestor is "" or ancestor == tax_id:  # if it's a blank or repeated, go up until finding ancestor
							ancestor = tax_path[i]
							_data[tax_id]["branch_length"] += 1
							i -= 1
						_data[tax_id]["ancestor"] = ancestor
				else:  # Otherwise populate the data
					_data[tax_id] = dict()
					_data[tax_id]["abundance"] = abundance
					_data[tax_id]["tax_path"] = tax_path
					if isinstance(rank_pos, int):  # might not be present
						_data[tax_id]["rank"] = rank
					if isinstance(tax_path_sn_pos, int):  # might not be present
						_data[tax_id]["tax_path_sn"] = tax_path_sn
					# Find the ancestor
					if len(tax_path) <= 1:
						_data[tax_id]["ancestor"] = "-1"  # no ancestor, it's a root
						_data[tax_id]["branch_length"] = 1
						ancestor = "-1"
					else:
						ancestor = tax_path[-2]
						_data[tax_id]["branch_length"] = 1
						i = -3
						while ancestor is "" or ancestor == tax_id:  # if it's a blank or repeated, go up until finding ancestor
							ancestor = tax_path[i]
							_data[tax_id]["branch_length"] += 1
							i -= 1
						_data[tax_id]["ancestor"] = ancestor
				# Create a placeholder descendant key initialized to [], just so each tax_id has a descendant key associated to it
				if "descendants" not in _data[tax_id]:  # if this tax_id doesn't have a descendant list,
					_data[tax_id]["descendants"] = list()  # initialize to empty list
				# add the descendants
				if ancestor in _data:  # see if the ancestor is in the data so we can add this entry as a descendant
					if "descendants" not in _data[ancestor]:  # if it's not present, create the descendant list
						_data[ancestor]["descendants"] = list()
					_data[ancestor]["descendants"].append(tax_id)  # since ancestor is an ancestor, add this descendant to it
				else:  # if it's not already in the data, create the entry
					_data[ancestor] = dict()
					_data[ancestor]["descendants"] = list()
					_data[ancestor]["descendants"].append(tax_id)

		# Unfortunately, some of the profile files may be missing intermediate ranks,
		# so we should manually populate them here
		# This will only really fix one missing intermediate rank....
		for key in _data.keys():
			if "abundance" not in _data[key]:  # this is a missing intermediate rank
				# all the descendants *should* be in there, so leverage this info
				if "descendants" not in _data[key]:
					print("You're screwed, malformed profile file with rank %s" % key)
					raise Exception
				else:
					descendant = _data[key]["descendants"][0]
					to_populate_key = descendant  # just need the first one since the higher up path will be the same
					to_populate = copy.deepcopy(_data[to_populate_key])
					tax_path = to_populate["tax_path"]
					tax_path_sn = to_populate["tax_path_sn"]
					descendant_pos = tax_path.index(descendant)
					for i in range(len(tax_path) - 1, descendant_pos - 1, -1):
						tax_path.pop(i)
						tax_path_sn.pop(i)
					to_populate["branch_length"] = 1
					if rank in to_populate:
						rank = to_populate["rank"]
						if rank == "strain":
							rank = "species"
						elif rank == "species":
							rank = "genus"
						elif rank == "genus":
							rank = "family"
						elif rank == "family":
							rank = "order"
						elif rank == "order":
							rank = "class"
						elif rank == "class":
							rank = "phylum"
						elif rank == "phylum":
							rank = "superkingdom"
						to_populate["ancestor"] = tax_path[-2]
					_data[key] = to_populate



		return

	def write_file(self, out_file_name=None):
		if out_file_name is None:
			raise Exception
		_data = self._data
		keys = _data.keys()
		# This will be annoying to keep things in order...
		# Let's iterate on the length of the tax_path since we know that will be in there
		tax_path_lengths = max([len(_data[key]["tax_path"]) for key in keys])
		fid = open(out_file_name, 'w')
		# Write the header
		for head in self._header:
			fid.write("%s\n" % head)

		# Loop over length of tax_path and write data
		# always make the output tax_id, rank, tax_path, tax_path_sn, abundance in that order
		for path_length in xrange(1, tax_path_lengths + 1):
			for key in keys:
				if len(_data[key]["tax_path"]) == path_length and _data[key]["abundance"] > self._eps:
					line_data = _data[key]
					fid.write("%s\t" % key)
					if self._rank_pos is not None:
						fid.write("%s\t" % line_data["rank"])
					fid.write("%s\t" % "|".join(line_data["tax_path"]))
					if self._tax_path_sn_pos is not None:
						fid.write("%s\t" % "|".join(line_data["tax_path_sn"]))
					fid.write("%f\n" % line_data["abundance"])
		fid.close()
		return

	def threshold(self, threshold=None):
		if threshold is None:
			raise Exception
		_data = self._data
		keys = _data.keys()
		for key in keys:
			if _data[key]["abundance"] < threshold:
				_data[key]["abundance"] = 0
		return

	def _subtract_down(self):
		# helper function to push all the weights up by subtracting
		# NOTE: when subtracting, need to start at root and go down
		# NOTE: when adding, need to start at leaves and go up
		_data = self._data
		keys = _data.keys()
		# This will be annoying to keep things in order...
		# Let's iterate on the length of the tax_path since we know that will be in there
		tax_path_lengths = max([len(_data[key]["tax_path"]) for key in keys])
		for path_length in range(1, tax_path_lengths):  # eg tax_path_lengths = 5, use 1,2,3,4 since we stop at leaves
			for key in keys:
				if len(_data[key]["tax_path"]) == path_length:
					descendants = _data[key]["descendants"]  # get all descendants
					for descendant in descendants:
						_data[key]["abundance"] -= _data[descendant]["abundance"]  # subtract the descendants abundance

	def _add_up(self):
		# helper function to push all the weights up by subtracting
		# NOTE: when subtracting, need to start at root and go down
		# NOTE: when adding, need to start at leaves and go up
		_data = self._data
		keys = _data.keys()
		# This will be annoying to keep things in order...
		# Let's iterate on the length of the tax_path since we know that will be in there
		tax_path_lengths = max([len(_data[key]["tax_path"]) for key in keys])
		for path_length in range(tax_path_lengths, 1, -1):  # eg tax_path_lengths = 5, use 5,4,3,2, since we stop at roots
			for key in keys:
				if len(_data[key]["tax_path"]) == path_length:
					ancestor = _data[key]["ancestor"]
					if ancestor in _data:  # don't do anything if this is a/the root node
						_data[ancestor]["abundance"] += _data[key]["abundance"]  # add the descendants abundance

	def normalize(self):
		# Need to really push it up while subtracting, then normalize, then push up wile adding
		# self._push_up(operation="subtract")
		self._subtract_down()
		_data = self._data
		keys = _data.keys()
		total_abundance = 0
		for key in keys:
			total_abundance += _data[key]["abundance"]
		# print(total_abundance)
		for key in keys:
			if total_abundance > 0:
				_data[key]["abundance"] /= total_abundance
				_data[key]["abundance"] *= 100  # make back into a percentage
		# self._push_up(operation="add")
		self._add_up()
		return

	def merge(self, other):
		# Warning: not checking for taxonomic consistency
		if not isinstance(other, Profile):
			print("Only works with other Profiles")
			raise Exception
		self._header.insert(0, "# This is a merged file, ignore files in headers below")
		_data = self._data
		_other_data = other._data
		other_keys = _other_data.keys()
		for key in other_keys:
			if key in _data:
				_data[key]["abundance"] += _other_data[key]["abundance"]  # if already in there, add abundances
			else:
				_data[key] = copy.copy(_other_data[key])  # otherwise use the whole thing

	def unifrac(self, other, eps=0):
		# I'm not sure this is giving the right answer....
		print("Don't think this is working")
		raise Exception
		if not isinstance(other, Profile):
			print("Must be a profile")
			raise Exception
		# For the fun of it, let's throw in the unifrac distance
		P = copy.deepcopy(self)  # make a copy of the data since we don't want to change it
		Q = copy.deepcopy(other)
		P.normalize()
		Q.normalize()
		P._subtract_down()
		Q._subtract_down()
		R = copy.deepcopy(P)  # this will be our partial sums
		# next, do partial_sums = P - Q
		Z = 0
		for key in Q._data.keys():
			if key in R._data:
				R._data[key]["abundance"] -= Q._data[key]["abundance"]  # Subtract Q from R
			else:
				R._data[key] = Q._data[key]  # Do I need to use copy here?
				R._data[key]["abundance"] = -R._data[key]["abundance"]  # Put -Q in the blank space of R
		# Since everything here is percentages, we need to divide to get back to fractions
		for key in R._data.keys():
			R._data[key]["abundance"] /= 100
		# Then push up the mass while adding
		for key in R._data.keys():
			val = R._data[key]["abundance"]
			if abs(val) > eps:
				if "ancestor" in R._data[key]:
					ancestor = R._data[key]["ancestor"]
					R._data[ancestor]["abundance"] += val
					Z += abs(val) * R._data[key]["branch_length"]
		return Z
