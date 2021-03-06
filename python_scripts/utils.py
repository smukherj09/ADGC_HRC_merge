""" Collection of utility scripts"""
import gzip

def get_size_file_mb(filename):
	return int(os.path.getsize(filename)/(1024*1024))

def get_mem(wildcards):
	print(wildcards)
	return int(get_size_mb('output.dat')*10)

def read_ref_file(rs_reference):
	rsRefs = {}
	with gzip.open(rs_reference, 'rt') as openRef:
		for line in openRef:
			line = line
			words = line.split()
			chrom = words[0]
			pos = words[1]
			rsid = words[2]
			ref = words[3]
			alt = words[4]
			for nuc in alt.split(','):
				rsRefs[f"{chrom}+{pos}+{ref}+{nuc}"] = rsid
	print("Done reading ref file")
	return rsRefs

def create_update_map(gen_file, ref_file, update_map):
	""" Creates 12 column variant id map updater for qctools"""
	gen_file = gen_file
	ref_file = ref_file
	out_file = update_map

	rs_ref = read_ref_file(ref_file)
	with gzip.open(gen_file, 'rt') as openfile, open(out_file, 'w') as out:
		out.write("SNPID rsid chromosome position a1 a2 new_SNPID new_rsid new_chrom new_pos new_a1 new_a2\n")
		for line in openfile:
			sline = line.split()
			SNPID, rsid, chromosome, position, a1, a2 = sline[:6]
			outline = []
			outline.extend(sline[:6])
			#22 22 22:16050435 16050435 T C 0.999
			#22 22 rs544901529 16352459 C T
			key = f"{SNPID}+{position}+{a1}+{a2}"
			new_id = rs_ref.get(key, None)
			if new_id is not None:
				outline.extend([SNPID, new_id, chromosome.split(":")[0], position, a1, a2])
				if len(outline) != 12:
					sys.exit("Failing outline not equal to 12.")
				out.write(' '.join(outline)+"\n")

def filter_related(preferred_samples, fam_file, mapping_id_file, pairwise_kinship, output):
	"""
	:param preferred_samples: ids of the unrelated case set to start with.
	:param covariate_file: File with case,control status
	:param mapping_id_file: File mapping short ids to long ids.
	:param pairwise_kinship: kinship coefficients for all samples
	:return:
	"""
	from collections import defaultdict
	# Load cases into final list of samples to keep.
	all_kinships = []
	samples_to_keep = []
	unrelated_cases = []
	with open(preferred_samples, 'r') as samps:
		for i, line in enumerate(samps):
			sline = line.strip().split()
			samples_to_keep.append("{} {}".format(sline[0], sline[1]))
	print(f"!!!!!! Added {i} unrelated case samples. Total samples = {len(samples_to_keep)}")

	# Load mapping_id_file into dictionary.
	status_map = {"control": [], "case": [], "missing": []}
	with open(mapping_id_file, 'r') as map_file:
		for line in map_file:
			sline = line.strip().split()
			key = ""
			if sline[2] == "1":
				key = "control"
			elif sline[2] == "2":
				key = "case"
			else:
				key = "missing"
			status_map[key].append("{} {}".format(sline[0], sline[1]))

	# remove samples related to cases
	sample_related_to_case = []
	all_kin_samples = set()
	with open(pairwise_kinship, 'r') as kin:
		header = next(kin)
		for line in kin:
			sline = line.strip().split()
			person1 = "{} {}".format(sline[0], sline[1])
			person2 = "{} {}".format(sline[2], sline[3])
			all_kin_samples.add(person1)
			all_kin_samples.add(person2)
			if person2 in samples_to_keep:
				# print("new sample_related_to_case")
				# if person2 is a case we are keeping, and person1 is not
				# if person1 in status_map['case']:
				# 	print(f"person1={person1}, person2={person2}")
				# 	input("This is not expected")
				sample_related_to_case.append(person1)
	print(f"Number of samples related to a case = {len(sample_related_to_case)}")
	# Algo goes:
	# 1. Add unrelated cases to samples to keep list
	# Loop through kinship output, ignoring cases.
	skipped_rel_case = 0
	missings = defaultdict(list)
	controls = defaultdict(list)
	# cases = defaultdict(list)
	with open(pairwise_kinship, 'r') as kin:
		dup, one, two, three = 0,0,0,0
		header = next(kin)
		for line in kin:
			# print(f"On line = {line}")
			sline = line.strip().split()
			person1 = "{} {}".format(sline[0], sline[1])
			person2 = "{} {}".format(sline[2], sline[3])
			all_kinships.append(person1+":"+person2)
			if person1 in sample_related_to_case:
				# Skip this person completely
				skipped_rel_case += 1
				pass
			else:
				if person1 in status_map['case']:
					# print("person1 is case")
					pass
					# # This sample is already in samples_to_keep.
					# cases[person1].append(person2)
				elif person1 in status_map['control']:
					# print("person1 is control")
					if (person2 in status_map['case'] and person2 not in samples_to_keep) or person2 in sample_related_to_case:
						# This relationship is with a case that will not be in the final set.
						pass
					else:
						# print("appending to")
						controls[person1].append(person2)
				elif person1 in status_map['missing']:
					# print("person1 is missing")
					if (person2 in status_map['case'] and person2 not in samples_to_keep) or person2 in sample_related_to_case:
						# This relationship is with a case that will not be in the final set.
						pass
					else:
						# print("appending to")
						missings[person1].append(person2)
				else:
					print("person1 = {} not in any status.".format(person1))
			kinship = float(sline[7])
			if kinship > 0.354:  # Dup
				dup += 1
			elif kinship > 0.1777:  # 1st
				one += 1
			elif kinship > 0.0884:  # 2nd
				two += 1
			elif kinship > 0.0442:  # 3rd
				three += 1
	print(f"skipped_rel_case = {skipped_rel_case}")
	print(f"Dup/MZ = {dup}")
	print(f"1st = {one}")
	print(f"2nd = {two}")
	print(f"3rd = {three}")
	print(f"Length of kin samples = {len(all_kin_samples)}")
	print(f"Len of samples to keep = {len(samples_to_keep)}")
	# Lets loop through missing and remove them
	sorted_missings = sorted(missings.items(), key=lambda kv: len(kv[1]), reverse=True)
	sorted_controls = sorted(controls.items(), key=lambda kv: len(kv[1]), reverse=True)
	sampe_of_interest = ["F9208 I9208", "F7249 I7249"]
	def remove_sample(person_to_remove):
		""" Loop through missing and controls to """
		debug = False
		if person_to_remove in sampe_of_interest:
			debug=True
		for i, (p1, related_list) in enumerate(sorted_missings):
			if related_list and person_to_remove in related_list:
				if debug:
					print(p1, related_list)
				sorted_missings[i] = (p1, related_list.remove(person_to_remove))
		for i, (p1, related_list) in enumerate(sorted_controls):
			if related_list and person_to_remove in related_list:
				if debug:
					print(p1, related_list)
				sorted_controls[i] = (p1, related_list.remove(person_to_remove))
	not_in_kin_not_case = 0
	with open(fam_file, 'r') as fam:
		for line in fam:
			sline = line.strip().split()
			sample = "{} {}".format(sline[0], sline[1])
			if sample not in all_kin_samples and sample not in samples_to_keep:
				# add_sample_to_final_output()
				if sample in sampe_of_interest:
					print(f"Adding not in kinship file sample {sample}")
				samples_to_keep.append(sample)
				not_in_kin_not_case += 1
	print(f"!!!!!! Added {not_in_kin_not_case} not_in_kin_not_case. Total samples = {len(samples_to_keep)}")
	removed_missings = 0
	added_missings = 0
	removed_controls = 0
	added_controls = 0
	for p1, related_list in sorted_missings:
		# print(p1, related_list)
		if related_list is None or len(related_list) == 0: # If this sample has relationships, remove it.
			added_missings += 1
			# print(f"adding sample p1={p1} to keep list.")
			if p1 in sampe_of_interest:
				print("missing Adding it {p1}, {related_list}")
			samples_to_keep.append(p1)
		else: # Otherwise, we can add it to samples_to_keep
			removed_missings += 1
			remove_sample(p1)
	print(f"!!!!!! Added {added_missings} Missing samples. Total samples = {len(samples_to_keep)}")
	for p1, related_list in sorted_controls:
		# print(p1, related_list)
		if related_list is None or len(related_list) == 0: # If no more relationships
			added_controls += 1
			# print(f"adding sample p1={p1} to keep list.")
			if p1 in sampe_of_interest:
				print(f"control Adding it {p1}, {related_list}")
			samples_to_keep.append(p1)
		else: # Otherwise, remove it
			removed_controls += 1
			remove_sample(p1) # Remove sample from any other relationship array it was in.
	print(f"!!!!!! Added {added_controls} Control samples. Total samples = {len(samples_to_keep)}")
	print(f"removed_missings = {removed_missings}")
	print(f"removed_controls = {removed_controls}")
	print(f"Len of samples to keep = {len(samples_to_keep)}")

	with open(output, 'w') as out:
		out.write('\n'.join(samples_to_keep))


def fix_vcf(input_vcf, chromNum):
	""" Strips the ,22 and adds the contig header. """
	import gzip
	import sys

	chromNum = str(chromNum)

	#open the vcf to be annotated and output into the open outputfile
	with gzip.open(input_vcf, 'rt') as openfile:
		for i, line in enumerate(openfile):
			line = line
			if not line.startswith('#'):
				sline = line.split()
				chrom, pos, id, ref, alt = sline[0], sline[1], sline[2], sline[3], sline[4]
				new_id = id.replace(f",{chromNum}", "")
				outline = [chromNum, pos]
				outline.append(new_id)
				outline.extend(sline[3:]) # Add the rest of the line unchanged
				outline += "\n"
				sys.stdout.write("\t".join(outline))
			else:
				sys.stdout.write(line)
				if i == 0:
					sys.stdout.write(f"##contig=<ID={chromNum}>\n")

def rs_update_gen(gen_file, ref_file, output):
	""" Loop through gen_file and update rsid column to real rsid.

	SNP ID, RS ID of the SNP, base-pair position of the SNP, the allele coded A and the allele coded B
	22      22                  22:17060707 17060707 G A

	 """
	import gzip

	outputfile = gzip.open(output, 'wt', compresslevel=3)
	#read the refile into a dictionary
	rsRefs = read_ref_file(ref_file)

	#open the vcf to be annotated and output into the open outputfile
	CHUNK = 40000
	print("Start parsing input gen")
	import time
	start = time.time()
	print("Working on line number: 0")
	with gzip.open(gen_file, 'rt') as openfile:
		write_chunk = []
		for i, line in enumerate(openfile):
			line = line
			if i != 0 and i % CHUNK == 0:
				print("Took {} seconds".format(time.time() - start))
				start = time.time()
				print("Working on line number: {}".format(i))
				if write_chunk is not None:
					outputfile.writelines(write_chunk)
					write_chunk = []
			sline = line.split()
			chrom = sline[0]
			rsid_chrom = sline[1]
			chrom_pos = sline[2]
			pos = sline[3]
			ref = sline[4]
			alt = sline[5]
			key = f"{chrom}+{pos}+{ref}+{alt}"
			# If we cant find an rsid, create a detailed variant id
			detailed_variant_id = f"{chrom}:{pos}:{ref}:{alt}"
			new_id = rsRefs.get(key, detailed_variant_id)
			outline = [chrom, new_id, pos, ref, alt]
			outline.extend(sline[6:]) # Add the rest of the line unchanged
			write_chunk.append(" ".join(outline)+"\n")
		if write_chunk:
			outputfile.writelines(write_chunk)
	outputfile.close()
	print("Done writing output gen: {}".format(output))

def create_remap_file(king_unrelated, id_map, unrelated_ids_plink, unrelated_ids_vcf):
	""" Given the king unrelated output, and the id_map I create originally,
	remap the short ids to long ids. The output will be used to prune the real
	final dataset ids.
	"""
	# ADC1_NACC548317_08AD7682___NACC548317_08AD7682 NACC548317_08AD7682 F1 I1
	id_map_dict = {}
	with open(id_map) as f:
		for line in f:
			sline = line.split()
			id_map_dict[f"{sline[2]}-{sline[3]}"] = f"{sline[0]} {sline[1]}"
	with open(king_unrelated) as f, open(unrelated_ids_plink, 'w') as out_plink, open(unrelated_ids_vcf, 'w') as out_vcf:
		for line in f:
			#FID_1   IID_1
			sline=line.split()
			out_plink.write(id_map_dict[f'{sline[0]}-{sline[1]}']+"\n")
			# Keep only first id for vcfs..
			out_vcf.write(id_map_dict[f'{sline[0]}-{sline[1]}'].split()[0]+"\n")
	print(f"Done writing output file: {unrelated_ids_plink} and {unrelated_ids_vcf}")

def dosage():
	""" Convert vcf to dosage. Requires AF in order to differentiate major/minor reference allele. If the AF is > .5 then
	the reference is taken as the minor allele. If the AF is lower than .5 the ref is taken as the major allele.
	"""
	import sys
	import re
	chunk = 10000
	# if in_vcf.endswith(".gz"):
	# 	vcf = gzip.open(in_vcf, 'rt')
	# else:
	# 	vcf = open(in_vcf, 'rt')
	# for i, line in enumerate(vcf.readlines()):
	for i, line in enumerate(sys.stdin):
		if i > 0  and i % chunk == 0:
			sys.stderr.write(f"On line number: {i}")
		sline = line.split()
		if line.startswith("##"):
			if line.startswith("##INFO"): # Stick in new format field.
				sys.stdout.write("##FORMAT=<ID=DS,Type=Float,Number=1,Description=\"Genotype dosage.\">\n")
			sys.stdout.write(line)
			pass
		elif line.startswith("#"):
			sline = line.lstrip("#").split()
			sys.stdout.write(line)
			header = sline
		else:
			hline = dict(zip(header, sline))
			af = hline['INFO'].split('=')
			m = re.search("AF=(\d+)", hline['INFO'])
			af = int(m.group(1))

			# Use current line, just add :DS to end of FORMAT column.
			current_line = f"{hline['CHROM']}\t{hline['POS']}\t{hline['ID']}\t{hline['REF']}\t{hline['ALT']}\t{hline['QUAL']}\t{hline['FILTER']}\t{hline['INFO']}\t{hline['FORMAT']}:DS"
			all_sample_data = []
			for sample in sline[9:]:
				format_list = hline['FORMAT'].split(":")
				hsample_data = dict(zip(format_list, sample.split(":")))
				gps = hsample_data['GP'].split(',')
				gps = list(map(float, gps))
				# print(gps)
				if len(gps) != 3:
					print("Expected 3 GP values found: {}".format(len(gps)))
					sys.exit(1)
				ds = 0
				# print(gps)
				if af >= 0.5:
					ds = gps[0] + gps[0] + gps[1]
				else:
					ds = gps[2] + gps[2] + gps[1]
				# Use current sample data, just add a :<calculated dosage> to the end.
				all_sample_data.append(f"{sample}:{ds}")
			joined_sample_data = '\t'.join(all_sample_data)
			current_line = f"{current_line}\t{joined_sample_data}"
			sys.stdout.write(current_line+"\n")

def rs_annotate(input_vcf, rs_reference, chromNum, output):
	import gzip

	outputfile = gzip.open(output, 'wt')
	chromNum = str(chromNum)
	#read the refile into a dictionary
	rsRefs = read_ref_file(ref_file)

	#open the vcf to be annotated and output into the open outputfile
	CHUNK = 1000
	print("start parsing input vcf")
	with gzip.open(input_vcf, 'rt') as openfile:
		write_chunk = []
		for i, line in enumerate(openfile):
			line = line
			if i != 0 and i % CHUNK == 0:
				print("Working on line number: {}".format(i))
				if write_chunk is not None:
					outputfile.writelines(write_chunk)
					write_chunk = []
			if not line.startswith('#'):
				sline = line.split()
				chrom = sline[0]
				pos = sline[1]
				id = sline[2]
				ref = sline[3]
				alt = sline[4]
				key = f"{chrom}+{pos}+{ref}+{alt}"
				new_id = rsRefs.get(key, id.replace(f",{chromNum}", ""))
				outline = [chromNum, pos]
				outline.append(new_id)
				outline.extend(sline[3:]) # Add the rest of the line unchanged
				outline += "\n"
				write_chunk.append("\t".join(outline))
			else:
				write_chunk.append(line)
				if i == 0:
					write_chunk.append(f"##contig=<ID={chromNum}>\n")
		if write_chunk:
			outputfile.writelines(write_chunk)
	outputfile.close()


def sample_from_fam(input, output):
	print("Running create_sample_file_from_fam with input={} and output={}".format(input, output))
	import os
	import sys
	"""Convert .fam files to .sample files for ADGC2.0 project.
	.fam

	Family ID ('FID')
	Within-family ID ('IID'; cannot be '0')
	Within-family ID of father ('0' if father isn't in dataset)
	Within-family ID of mother ('0' if mother isn't in dataset)
	Sex code ('1' = male, '2' = female, '0' = unknown)
	Phenotype value ('1' = control, '2' = case, '-9'/'0'/non-numeric = missing data if case/control)

	ACT_ACT150544 ACT150544 0 0 -9 -9
	ACT_ACT94662 ACT94662 0 0 1 1
	ACT_ACT94442 ACT94442 0 0 1 1
	ACT_ACT92870 38013785 0 0 -9 -9
	ACT_ACT90327 ACT90327 0 0 1 1

	converted from 1/0 to 2/1 case/control coding).
	to .sample
	ID_1 ID_2 missing case cov_1
	0 0 0 B C
	sample1 1 0
	sample2 2 0
	sample3 2 0
	sample4 2 1
	sample4 0 NA
	"""
	HEADER = "ID_1 ID_2 missing sex case\n"
	HEADER_DESC = "0 0 0 D B\n"
	if len(input) != 1 or len(output) != 1:
		sys.exit(-1)

	fam_file = input[0]
	sample_file = output[0]
	print("Writing to output file: {}".format(sample_file))
	if not fam_file.endswith('.fam'):
		print("Input fam file must end with .fam!")
		sys.exit(-1)
	if os.path.exists(sample_file):
		print("{} already exists!".format(sample_file))
		sys.exit(-1)
	print("Writing sample file: {}".format(sample_file))
	with open(fam_file) as fam, open(sample_file, 'w+') as sample:
		# Write header lines
		sample.write(HEADER)
		sample.write(HEADER_DESC)
		for line in fam:
			sline = line.split()

			sample_unique_id = "{}___{}".format(sline[0], sline[1])
			sex = sline[4]
			sample_sex = ""
			if sex == "1":
				sample_sex = "1"
			elif sex == "2":
				sample_sex = "2"
			elif sex == "-9" or sex == "0":
				sample_sex = "0"
			else:
				print("Error reading fam file. Unkown sex code: {}".format(sex))
				sys.exit(-1)
			# 3. Grab case/control status 6th column
			# Phenotype value ('1' = control, '2' = case, '-9'/'0'/non-numeric = missing data if case/control)
			pheno = sline[5]
			sample_pheno = ""
			if pheno == "1":
				sample_pheno = "0"
			elif pheno == "2":
				sample_pheno = "1"
			elif pheno == "-9":
				sample_pheno = "NA"
			else:
				print("Error reading fam file. Unknown phenotype code: {}".format(pheno))
				sys.exit(-1)

			# Write data to new sample file
			# Use a combined ID_1___ID_2 as the first ID because thats sane.
			sample.write("{} {} 0 {} {}\n".format(sample_unique_id, sline[1], sample_sex, sample_pheno))
