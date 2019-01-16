#!/usr/bin

import xlrd
import sys
import re
from string import Template


cb_fullmatch_temp='''
	$DATA_TYPE	$DATA_NAME;'''

cb_fullmatch_reserved='''
	$DATA_TYPE	reserved_B${START_BYTE}_${END_BYTE};'''

cb_partmatch_reserved='''
			$DATA_TYPE	reserved_b${START_BIT}_${END_BIT}		: $DATA_LENGTH;'''

cb_partmatch_temp='''
			$DATA_TYPE	$DATA_NAME		: $DATA_LENGTH;'''

cb_partmatch_head='''
	union{
		struct{$DATA_BODY
		}bits;
		$FMT_TYPE vals;
	}B${START_BYTE}_${END_BYTE}
'''


def getFrameFormat():
	frameFormats = []
	
	# 8 uint8
	frameFormat = [1,1,1,1,1,1,1,1]
	frameFormats.append(frameFormat)
	
	# 6 uint8, 1 uint16
	frameFormat = [1,1,1,1,1,1]
	for i in range (0, len(frameFormat)):
		frameFormat_tmp = frameFormat[:]
		frameFormat_tmp.insert(i, 2)
		frameFormats.append(frameFormat_tmp)
	
	
	# 4 uint8, 2 uint16
	frameFormat = [1,1,1,1]
	for m in range(len(frameFormat)):
		format_tmp1 = frameFormat[:]
		format_tmp1.insert(m, 2)
		for n in range(len(format_tmp1)):
			format_tmp2 = format_tmp1[:]
			format_tmp2.insert(n, 2)
			frameFormats.append(format_tmp2)
	
	
	# 2 uint8, 3 uint16
	frameFormat = [2,2,2]
	for m in range(len(frameFormat)):
		format_tmp1 = frameFormat[:]
		format_tmp1.insert(m, 1)
		for n in range(len(format_tmp1)):
			format_tmp2 = format_tmp1[:]
			format_tmp2.insert(n, 1)
			frameFormats.append(format_tmp2)
	
	# 0 uint8, 4 uint16
	frameFormat = [2,2,2]
	frameFormats.append(frameFormat)
	
	# 4 uint8, 1 uint32
	frameFormat = [1,1,1,1]
	for i in range (0, len(frameFormat)):
		frameFormat_tmp = frameFormat[:]
		frameFormat_tmp.insert(i, 4)
		frameFormats.append(frameFormat_tmp)
	
	# 2 uint8, 1 uint16, 1 uint32
	frameFormat = [1,1]
	for m in range(len(frameFormat)):
		format_tmp1 = frameFormat[:]
		format_tmp1.insert(m, 2)
		for n in range(len(format_tmp1)):
			format_tmp2 = format_tmp1[:]
			format_tmp2.insert(n, 4)
			frameFormats.append(format_tmp2)
	
	# 2 uint16, 1 uint32
	frameFormat = [2,2]
	for i in range (0, len(frameFormat)):
		frameFormat_tmp = frameFormat[:]
		frameFormat_tmp.insert(i, 4)
		frameFormats.append(frameFormat_tmp)
	
	# 2 uint32
	frameFormat = [4,4]
	frameFormats.append(frameFormat)
	
	# 1 uint64
	frameFormat = [8]
	frameFormats.append(frameFormat)
	
	# 删除重复的模型
	ret = []
	for ff in frameFormats:
		if ff not in ret:
			ret.append(ff)
	
	return ret
	



class Frame:
	name = ''
	id = 0x0
	type = 's'	# s-send; r-receive
	period = 1000
	length = 8
	signals = []	# 信号内容

	def __init__(self, name = '', id = 0, period = 1000, length = 8):
		print("%s***********************"%sys._getframe().f_code.co_name)
		self.name = name
		self.id = id
		self.period = period
		self.length = length
		
	def setFrame(self, name = '', type='s', id = 0, period = 1000, length = 8):
		print("%s***********************"%sys._getframe().f_code.co_name)
		self.name = name
		self.id = id
		self.type = type
		self.period = period
		self.length = length
	
	# 将从excel表中获取一行信号的内容插入到self.signals中，按照start_bit值从小到大排列
	def setSignal(self, name, meaning = '', start_bit = 0, length = 1, type = "unsigned", resolution = 1, factor = 1, min = 0, max = 0, init = 0, invalid = 0, unit = '', comment = ''):
		print("%s***********************"%sys._getframe().f_code.co_name)
		insert_off = 0
		for i in range(len(self.signals)):
			#print("start_bit=%f, self.signals[%d].start_bit=%f"%(start_bit, i, self.signals[i]["start_bit"]))
			if start_bit > self.signals[i]["start_bit"]:
				insert_off += 1
			else:
				break
		#print("insert_off=%d`, start_bit=%f"%(insert_off, start_bit))
		self.signals.insert(insert_off, {"name":name, "meaning":meaning, "start_bit":start_bit, "length":length, "type":type, "resolution":resolution, "factor":factor, "min":min, "max":max, "init":init,"invalid":invalid, "unit":unit, "comment":comment})
		#self.signals.append({"name":name, "meaning":meaning, "start_bit":start_bit, "length":length, "type":type, "resolution":resolution, "factor":factor, "min":min, "max":max, "init":init,"invalid":invalid, "unit":unit, "comment":comment})


	def getsignal(self, offset):
		print("%s***********************"%sys._getframe().f_code.co_name)
		if offset <= len(self.signals):
			return self.signals[0]
		else:
			print("req_offset:%d, signal_size:%d"%(offset, len(self.signals)))
			return {}
	
	def printFrame(self):
		print("%s***********************"%sys._getframe().f_code.co_name)
		print("id=%s,name=%s,period=%s"%(self.id, self.name, self.period))

	def printSignal(self):
		print("%s***********************"%sys._getframe().f_code.co_name)
		print("count of signal:%d"%len(self.signals))
		for sig in self.signals:
			print(sig)
			print('')	# 输出空行

	def getMatchedFormat(self, frameFormats):
		for ff in frameFormats:
			need_next_ff = False
			for sig in self.signals:
				sig_data_start = int(sig["start_bit"] / 8)
				sig_data_end = int((sig["start_bit"] + sig["length"] - 1) / 8)
				fmt_first = 0
				fmt_second = 0
				start_idx = 0
				end_idx = 0
				for idx in range(len(ff)):
					fmt_second += ff[idx]
					if fmt_first <= sig_data_start < fmt_second:
						start_idx = idx
					if fmt_first <= sig_data_end < fmt_second:
						end_idx = idx
					fmt_first += ff[idx]
				if start_idx != end_idx:
					need_next_ff = True
					break

			comment = '''

				data_bytes = sig_data_end - sig_data_start + 1
				st = 0
				# 识别模型是否满足某个信号
				valid_flag = False
				for idx in range(len(ff)):
					if st <= sig_data_start and data_bytes <= ff[idx]:
						valid_flag = True
						break
					else:
						st += ff[idx]
				# 模型不满足该信号
				if not valid_flag:
					need_next_ff = True
					break'''
			if not need_next_ff:
				print("find frameFormat:")
				print(ff)
				return ff

	def getDataTypeStr(self, sig, length):
		data_type = ''
		if sig["type"].find("unsigned") != -1:
			data_type = "uint" + str(int(length)) + "_t"
		elif sig["type"].find("signed") != -1:
			data_type = "int" + str(int(length)) + "_t"
		elif sig["type"].find("float") != -1:
			data_type = "float"
		elif sig["type"].find("double") != -1:
			data_type = "double"
		else:
			print("unknow message type, signal: %s"%(sig["name"]))
			sys.exit()
		return data_type
		

	def getFrameStructStr(self):
		# 先确认获取的数据是否符合规范
		cur_pos = 0
		if len(self.signals)  == 0:
			print("without signals, please check message(id=%s) in %s"%(self.id, sys.argv[1]))
			sys.exit()	# 不应该未定义信号的报文存在
		for sig in self.signals:
			#if sig["start_bit"] <= cur_pos and cur_pos != 0:
			if sig["start_bit"] < cur_pos:
				print("message invalid: id=%s, signal=%s, start_bit error(start_bit:%d, cur_pos:%d)"%(self.id, sig["name"], sig["start_bit"], cur_pos))
				sys.exit()
			else:
				cur_pos = sig["start_bit"]

			if cur_pos + sig["length"] > 64:
				print("message invalid: id=%s, signal=%s, start_bit+length=%f"%(self.id, sig["name"], sig["start_bit"] + sig["length"]))
			else:
				cur_pos += sig["length"]
		
		#print("message correct, id=%s"%self.id)
		# 确定数据符合的模型
		frameFormats = getFrameFormat()
		matched_format = self.getMatchedFormat(frameFormats)

		# 根据模型和信号生成CAN报文结构体内容
		fmt_start_bit = 0
		fmt_end_bit = 0
		fmt_cur_offset = 0
		for sig_format in matched_format:
			fmt_end_bit = fmt_start_bit + sig_format * 8 - 1
			fmt_cur_offset = 0
			#print("fmt_start_bit=%d, fmt_end_bit=%d"%(fmt_start_bit, fmt_end_bit))
			fmt_body_str = ''
			fmt_str = ''
			fmt_used_union = False

			for sig in self.signals:
				sig_data_start = int(sig["start_bit"])
				sig_data_end   = int(sig["start_bit"] + sig["length"] - 1)

                # 判断信号是否在模型本单元内
				if sig_data_start > fmt_end_bit or sig_data_end < fmt_start_bit:
					continue
				if sig_data_start > (fmt_start_bit+fmt_cur_offset): # 模型单元中，本信号前还有预留的数据区
					#print("填充报文前的预留数据")
					strTmp = Template(cb_partmatch_reserved)
					data_type = "uint" + str(int(sig_format * 8)) + "_t"
					start_bit = int(fmt_cur_offset)
					end_bit = (sig_data_start - 1)
					start_bit_str = str(start_bit - fmt_start_bit)
					end_bit_str = str(end_bit - fmt_start_bit) if (end_bit - start_bit) > 1 else ''
					formatStr = strTmp.substitute(DATA_TYPE=data_type, START_BIT=start_bit_str, END_BIT=end_bit_str, DATA_LENGTH=str(sig_data_start - fmt_cur_offset))
					#print(formatStr)
					fmt_body_str += formatStr
					fmt_cur_offset = sig_data_start - fmt_start_bit

				# 填充信号到模型中
				if sig_data_start == fmt_start_bit and sig_data_end == fmt_end_bit:     #模型单元刚好被这一个信号填充完
					#print("刚好填充一个信号")
					strTmp = Template(cb_fullmatch_temp)
					data_type = self.getDataTypeStr(sig, sig_format * 8)
					formatStr = strTmp.substitute(DATA_TYPE = data_type, DATA_NAME = sig["name"])
					#print(formatStr)	#输出报文内容
					fmt_body_str += formatStr
					#break   # 模型单元被填充完后不会有其他信号处于该模型单元内
				else:
					fmt_used_union = True
					#print("填充单个信号")
					strTmp = Template(cb_partmatch_temp)
					data_type = self.getDataTypeStr(sig, sig_format * 8)
					formatStr = strTmp.substitute(DATA_TYPE = data_type, DATA_NAME=sig["name"],DATA_LENGTH = int(sig["length"]))
					#print(formatStr)	#输出报文内容
					fmt_body_str += formatStr
					fmt_cur_offset = int(sig["start_bit"] + sig["length"]) - fmt_start_bit # 模型单元接下来处理的起始位置设置为本信号结束位置的后一bit
					continue # 处理下一个信号
			if fmt_cur_offset < sig_format * 8: # 本模型单元中还有数据区为填充
				if fmt_cur_offset == 0: # 模型中没有填入任何数据
					# 填充完成预留的模型单元
					#print("填充预留的模型单元")
					strTmp = Template(cb_fullmatch_reserved)
					data_type = "uint" + str(int(sig_format * 8)) + "_t"
					start_byte_str = str(int(fmt_start_bit/8))
					end_byte_str = str(fmt_start_bit/8 + sig_format) if sig_format > 1 else ''
					formatStr = strTmp.substitute(DATA_TYPE=data_type, START_BYTE=start_byte_str, END_BYTE=end_byte_str)
					#print(formatStr)
					fmt_body_str += formatStr
				else:     
					#print("填充本模型单元尾部的预留区域")
					strTmp = Template(cb_partmatch_reserved)
					data_type = "uint" + str(int(sig_format * 8)) + "_t"
					start_bit = int(fmt_cur_offset)
					end_bit = sig_format*8 - 1
					start_bit_str = str(fmt_cur_offset)
					end_bit_str = str(end_bit) if (end_bit - start_bit) > 1 else ''
					formatStr = strTmp.substitute(DATA_TYPE=data_type, START_BIT=start_bit_str, END_BIT=end_bit_str, DATA_LENGTH=str(sig_data_start - fmt_cur_offset))
					#print(formatStr)
					fmt_body_str += formatStr
			if fmt_used_union:
				strTmp = Template(cb_partmatch_head)
				fmt_type = "uint" + str(sig_format) + "_t"
				start_byte = str(int(fmt_start_bit/8))
				end_byte = str(int(fmt_end_bit/8)) if sig_format > 1 else ''
				fmt_str = strTmp.substitute(DATA_BODY=fmt_body_str, FMT_TYPE = fmt_type, START_BYTE = start_byte, END_BYTE = end_byte)
			else:
				fmt_str = fmt_body_str
			print(fmt_str)	# output format unit string
			fmt_start_bit += sig_format * 8 # 设置模型处理的下一个单元的起始地址


						
def validateTitle(title):
	rstr = r"[\=\(\)\,\/\\\:\*\?\"\<\>\|\' ']" # '= ( ) ， / \ : * ? " < > |  '   还有空格 
	new_title = re.sub(rstr, "_", title) # 替换为下划线 
	return new_title




if len(sys.argv) != 2:
	print("usage: %s [**.xls]")
	sys.exit()
data = xlrd.open_workbook(sys.argv[1])
table = data.sheets()[3]
nrows = table.nrows 
start = False
frame = Frame()
for i in range(nrows):
	if i == 0:
		continue
	
	if table.cell(i,0).ctype != 0:
		if not start:
			name   = table.cell_value(i,0)
			type   = table.cell_value(i,1)
			id	   = table.cell_value(i,2)
			period = table.cell_value(i,3)
			length = table.cell_value(i,4)
			frame.setFrame(name = name, type = type, id = id, period = period, length = length)
			start = True
		else:
			print("**************")
			break
	else:
		print("setSignal")
		name = table.cell_value(i, 5)
		name = validateTitle(name)

		meaning = table.cell_value(i, 6)
		start_bit = table.cell_value(i, 7)
		length = table.cell_value(i, 8)
		comment = table.cell_value(i, 17).strip().replace('\n', ';')
		frame.setSignal(name = name, meaning = meaning, start_bit = start_bit, length = length, comment = comment)

frame.printFrame()
frame.printSignal()
frame.getFrameStructStr()
