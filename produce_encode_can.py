#!/usr/bin

import xlrd
import sys
import os
import re
import gflags
from string import Template

import temp_string

Flags = gflags.FLAGS

gflags.DEFINE_string('channel', 'can0', 'using can channel')  
gflags.DEFINE_string('proto_file', 'example.dbc', 'can protocol file, valid format: .xlsx .dbc')  
gflags.DEFINE_integer('sheet_numb', 0, 'if protocol file is a excel file, this flag mean which sheet in file')  
gflags.DEFINE_integer('circle_period', 50, 'can transmit thread running period')  
gflags.DEFINE_string('node_name', 'ADAS', 'network node name')  
gflags.DEFINE_string('output_file', 'do_process_rsq.cpp', 'output file name')  
gflags.DEFINE_boolean('enable_receive', False, 'if enable can receive') 
gflags.DEFINE_boolean('enable_sendSplit', False, 'if create thread for can send') 
gflags.DEFINE_boolean('enable_loopback', True, 'if enable can loopback function') 
gflags.DEFINE_boolean('enable_valueTable', True, 'if output signal value table') 
gflags.DEFINE_boolean('enable_comment', True, 'if output signal comment') 




def validateName(title):
	rstr = r"[\=\(\)\,\/\\\:\*\?\"\<\>\|\' ']" # '= ( ) ， / \ : * ? " < > |  '   还有空格 
	new_title = re.sub(rstr, "_", title) # 替换为下划线 
	return new_title.lower()

def validateBody(body):
	rstr = r"[\=\(\)\,\/\\\:\*\?\"\<\>\|\' ']" # '= ( ) ， / \ : * ? " < > |  '   还有空格 
	new_body = re.sub(rstr, "", body) # 删除特殊字符 
	return (new_body.lower())



def getDataTypeStr(sig, length):
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
		print("unknow message type, signal: %s, type:%s"%(sig["name"], sig["type"]))
		sys.exit()
	return data_type


def getFrameFormat():
	frameFormats = []
	
	# 8 uint8
	frameFormat = [1,1,1,1,1,1,1,1]
	frameFormats.append(frameFormat)
	
	# 6 uint8, 1 uint16
	frameFormat = [1,1,1,1,1,1]
	for i in range (0, len(frameFormat)+1):
		frameFormat_tmp = frameFormat[:]
		frameFormat_tmp.insert(i, 2)
		frameFormats.append(frameFormat_tmp)
	
	
	# 4 uint8, 2 uint16
	frameFormat = [1,1,1,1]
	for m in range(len(frameFormat)+1):
		format_tmp1 = frameFormat[:]
		format_tmp1.insert(m, 2)
		for n in range(len(format_tmp1)+1):
			format_tmp2 = format_tmp1[:]
			format_tmp2.insert(n, 2)
			frameFormats.append(format_tmp2)
	
	
	# 2 uint8, 3 uint16
	frameFormat = [2,2,2]
	for m in range(len(frameFormat)+1):
		format_tmp1 = frameFormat[:]
		format_tmp1.insert(m, 1)
		for n in range(len(format_tmp1)+1):
			format_tmp2 = format_tmp1[:]
			format_tmp2.insert(n, 1)
			frameFormats.append(format_tmp2)
	
	# 0 uint8, 4 uint16
	frameFormat = [2,2,2,2]
	frameFormats.append(frameFormat)
	
	# 4 uint8, 1 uint32
	frameFormat = [1,1,1,1]
	for i in range (0, len(frameFormat)+1):
		frameFormat_tmp = frameFormat[:]
		frameFormat_tmp.insert(i, 4)
		frameFormats.append(frameFormat_tmp)
	
	# 2 uint8, 1 uint16, 1 uint32
	frameFormat = [1,1]
	for m in range(len(frameFormat)+1):
		format_tmp1 = frameFormat[:]
		format_tmp1.insert(m, 2)
		for n in range(len(format_tmp1)+1):
			format_tmp2 = format_tmp1[:]
			format_tmp2.insert(n, 4)
			frameFormats.append(format_tmp2)
	
	# 2 uint16, 1 uint32
	frameFormat = [2,2]
	for i in range (0, len(frameFormat)+1):
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
	def __init__(self, name = '', id = 0, period = 0, length = 8, type = 's', comment=''):
		self.name = name
		self.id = id
		self.period = period
		self.length = length
		self.type = type
		self.comment = comment
		self.signals = []
		
	def setFrame(self, name = '', type='x', id = 0, period = 0, length = 8, comment = ''):
		self.name = name
		self.id = id
		self.type = type
		self.period = period
		self.length = length
		self.comment = comment
	
	# 将从excel表中获取一行信号的内容插入到self.signals中，按照start_bit值从小到大排列
	def setSignal(self, name, meaning = '', start_bit = 0, length = 1, type = "unsigned", factor = 1, offset = 1, rangefrom = 0, rangeto = 0, init = 0, invalid = '', unit = '', comment = ''):
		insert_off = 0
		for i in range(len(self.signals)):
			if start_bit > self.signals[i]["start_bit"]:
				insert_off += 1
			else:
				break
		self.signals.insert(insert_off, {"name":name, "meaning":meaning, "start_bit":start_bit, "length":length, "type":type, "factor":factor, "offset":offset, "rangefrom":rangefrom, "rangeto":rangeto, "init":init,"invalid":invalid, "unit":unit, "comment":comment})


	# 从所有的数据模型中获取本组信号匹配的模型
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

			if not need_next_ff:
				return ff
			return []

		
	def getFrameStructStr(self):
		return self.frameStructStr
	
	def getSendFrameInfo(self):
		strTmp = Template(temp_string.can_send_msg_temp)
		name = "cans_" + self.name
		delay = self.period if self.period != 0 else '_unknown_'
		ret = strTmp.substitute(ID=self.id, DELAY=delay, MSG=name, LEN=self.length)
		return ret

	def setFrameStructStr(self):
		# 先确认获取的数据是否符合规范
		cur_pos = 0
		if len(self.signals)  == 0:
			print("without signals, please check message(id=%s) in %s"%(self.id, sys.argv[1]))
			sys.exit()	# 不应该有未定义信号的报文存在
		for sig in self.signals:
			if sig["start_bit"] < cur_pos:
				print("message invalid: id=%s, signal=%s, start_bit error(start_bit:%d, cur_pos:%d)"%(self.id, sig["name"], sig["start_bit"], cur_pos))
				sys.exit()
			else:
				cur_pos = sig["start_bit"]

			if cur_pos + sig["length"] > 64:
				print("message invalid: id=%s, signal=%s, start_bit+length=%f"%(self.id, sig["name"], sig["start_bit"] + sig["length"]))
			else:
				cur_pos += sig["length"]
		
		# 确定数据符合的模型
		frameFormats = getFrameFormat()
		matched_format = self.getMatchedFormat(frameFormats)

		# 根据模型和信号生成CAN报文结构体内容
		fmt_start_bit = 0
		fmt_end_bit = 0
		fmt_cur_offset = 0
		fmts_str = ''
		for sig_format in matched_format:
			fmt_end_bit = fmt_start_bit + sig_format * 8 - 1
			fmt_cur_offset = 0
			fmt_body_str = ''
			fmt_str = ''
			fmt_used_union = False

			for sig in self.signals:
				sig_data_start = int(sig["start_bit"])
				sig_data_end   = int(sig["start_bit"] + sig["length"] - 1)

				data_type = getDataTypeStr(sig, int(sig_format * 8))
				invalid = "invalid:" + sig["invalid"] + '; ' if sig["invalid"] != '' else ''
				factor = "factor:" + sig["factor"] + '; ' if sig["factor"] != '' else ''
				offset = "offset:" + sig["offset"] + '; ' if sig["offset"] != '' else ''
				unit = "unit:" + sig["unit"] + ';' if sig["unit"] != '' else ''
				meaning = "value:" + sig["meaning"] + '; ' if sig["meaning"] != '' else ''
				if not Flags.enable_valueTable:
					meaning = ''
				desc = "description:" + sig["comment"] + '; ' if sig["comment"] != '' else ''
				if not Flags.enable_comment:
					desc = ''
                # 判断信号是否在模型本单元内
				if sig_data_start > fmt_end_bit or sig_data_end < fmt_start_bit:
					continue
				if sig_data_start > (fmt_start_bit+fmt_cur_offset): # 模型单元中，本信号前还有预留的数据区
					#print("填充报文前的预留数据")
					strTmp = Template(temp_string.cb_partmatch_reserved_none)
					data_type = "uint" + str(int(sig_format * 8)) + "_t"
					start_bit = int(fmt_cur_offset)
					end_bit = (sig_data_start - 1)
					start_bit_str = str(fmt_cur_offset)#str(start_bit - fmt_start_bit)
					end_bit_str = str(end_bit - fmt_start_bit) if (end_bit - start_bit) > 1 else ''
					formatStr = strTmp.substitute(DATA_TYPE=data_type, DATA_LENGTH= str(sig_data_start - fmt_start_bit))#str(sig_data_start - fmt_cur_offset))
					fmt_body_str += formatStr
					fmt_cur_offset = sig_data_start - fmt_start_bit

				# 填充信号到模型中
				if sig_data_start == fmt_start_bit and sig_data_end == fmt_end_bit:     #模型单元刚好被这一个信号填充完
					#print("刚好填充一个信号")
					strTmp = Template(temp_string.cb_fullmatch_temp)
					formatStr = strTmp.substitute(DATA_TYPE = data_type, DATA_NAME = sig["name"], MIN_VAL=sig["rangefrom"], MAX_VAL=sig["rangeto"], INVALID=invalid, FACTOR=factor, OFFSET=offset, UNIT=unit, MEANING=meaning, DESCRIPTION=desc)
					fmt_body_str += formatStr
					fmt_cur_offset = sig_format * 8
					#break   # 模型单元被填充完后不会有其他信号处于该模型单元内
				else:
					fmt_used_union = True
					strTmp = Template(temp_string.cb_partmatch_temp)
					data_type = getDataTypeStr(sig, int(sig_format * 8))
					formatStr = strTmp.substitute(DATA_TYPE = data_type, DATA_NAME=sig["name"],DATA_LENGTH = int(sig["length"]), MIN_VAL=sig["rangefrom"], MAX_VAL=sig["rangeto"], INVALID=invalid, FACTOR=factor, OFFSET=offset, UNIT=unit, MEANING=meaning, DESCRIPTION=desc)
					fmt_body_str += formatStr
					fmt_cur_offset = int(sig["start_bit"] + sig["length"]) - fmt_start_bit # 模型单元接下来处理的起始位置设置为本信号结束位置的后一bit
					continue # 处理下一个信号
			if fmt_cur_offset < sig_format * 8: # 本模型单元中还有数据区为填充
				if fmt_cur_offset == 0: # 模型中没有填入任何数据
					# 填充完成预留的模型单元
					#print("填充预留的模型单元")
					strTmp = Template(temp_string.cb_fullmatch_reserved)
					data_type = "uint" + str(int(sig_format * 8)) + "_t"
					start_byte_str = str(int(fmt_start_bit/8))
					end_byte_str = str(int(fmt_start_bit/8 + sig_format) - 1) if sig_format != 1 else ''
					formatStr = strTmp.substitute(DATA_TYPE=data_type, START_BYTE=start_byte_str, END_BYTE=end_byte_str)
					fmt_body_str += formatStr
				else:     
					#print("填充本模型单元尾部的预留区域")
					strTmp = Template(temp_string.cb_partmatch_reserved_none)
					data_type = "uint" + str(int(sig_format * 8)) + "_t"
					start_bit = int(fmt_cur_offset)
					end_bit = sig_format*8 - 1
					start_bit_str = str(fmt_cur_offset)
					end_bit_str = str(end_bit) if (end_bit - start_bit) > 1 else ''
					formatStr = strTmp.substitute(DATA_TYPE=data_type, DATA_LENGTH=str(end_bit - start_bit + 1))
					fmt_body_str += formatStr
			if fmt_used_union:
				strTmp = Template(temp_string.cb_partmatch_head)
				fmt_type = "uint" + str(sig_format*8) + "_t"
				start_byte = str(int(fmt_start_bit/8))
				end_byte = str(int(fmt_end_bit/8)) if sig_format > 1 else ''
				fmt_str = strTmp.substitute(DATA_BODY=fmt_body_str, FMT_TYPE = fmt_type, START_BYTE = start_byte, END_BYTE = end_byte)
			else:
				fmt_str = fmt_body_str
			fmts_str += fmt_str
			fmt_start_bit += sig_format * 8 # 设置模型处理的下一个单元的起始地址

		frame_str_temp = Template(temp_string.cb_frame_tmp)
		prd_str = self.period if self.period != 0 else ''
		self.frameStructStr = frame_str_temp.substitute(RDWR=self.type, CANID=str(self.id), PERIOD=prd_str, COMMENT=self.comment, NAME=self.name, FRAME_BODY = fmts_str)
	

excelFormat = {"framename":0, "frametype":1, "frameid":2, "period":3, "framelength":4, "signalname":5, "startbit":6, "signallength":7, "signaltype":8, "value":9, "offset":10, "factor":11, "rangefrom":12, "rangeto":13, "unit":14, "init":15, "invalid":16, "description":17}
						
def getExcelFormat(row_value):
	global excelFormat
	rstr = r"[\=\(\)\,\/\\\:\*\?\"\<\>\|\' '_]" # '= ( ) ， / \ : * ? " < > |  '   还有空格 
	for idx in range(len(row_value)):
		str1 = re.sub(rstr, "", row_value[idx]).lower()
		for key in excelFormat:
			if str1.find(key) != -1:
				print("%s:%d"%(key, idx))
				excelFormat[key] = idx
				break
	print(excelFormat)
			


				
# 从excel表中导入CAN协议
def getCanFrameFromExcel(filename, sheet_offset=0):
	if len(sys.argv) < 2 or len(sys.argv) > 3:
		print("usage: %s <**.xls> [sheet offset,default=0]"%sys.argv[0])
		print("eg1: %s test.xlsx 1"%sys.argv[0])
		print("eg1: %s test.xlsx"%sys.argv[0])
		sys.exit()
	data = xlrd.open_workbook(filename)
	table = data.sheets()[sheet_offset]
	nrows = table.nrows 
	print("excel: nrows = %d"%nrows)
	start = False
	canMsg = []
	cur_msg_idx = 0
	# 创建一个类列表，数量等于行号
	for i in range(nrows):
		canMsg.append(Frame())
	
	for i in range(nrows):
		if i == 0:
			print(table.row_values(0))
			getExcelFormat(table.row_values(0))
			continue
		if table.cell(i,0).ctype != 0:
			name   = validateName(table.cell_value(i, excelFormat["framename"]))
			type   = validateBody(table.cell_value(i, excelFormat["frametype"]))
			id	   = table.cell_value(i, excelFormat["frameid"])
			period = table.cell_value(i, excelFormat["period"])
			length = table.cell_value(i, excelFormat["framelength"])
			canMsg[cur_msg_idx].setFrame(name = name, type = type, id = id, period = period, length = length)
	
		sig_name = validateName(table.cell_value(i, excelFormat["signalname"]))
		if sig_name == '':
			continue
	
		sig_meaning = str(table.cell_value(i, excelFormat["value"])).replace("\n", ";").lower()
		sig_start_bit = table.cell_value(i, excelFormat["startbit"])
		sig_length = table.cell_value(i, excelFormat["signallength"])
		sig_type = validateBody(table.cell_value(i, excelFormat["signaltype"]))
		factor = str(table.cell_value(i, excelFormat["factor"])).lower()	# 先只设置为字符串类型
		offset = str(table.cell_value(i, excelFormat["offset"])).lower()
		rangefrom = str(table.cell_value(i, excelFormat["rangefrom"])).lower()
		rangeto = str(table.cell_value(i, excelFormat["rangeto"])).lower()
		init = str(table.cell_value(i, excelFormat["init"])).lower()
		invalid = str(table.cell_value(i, excelFormat["invalid"])).lower()
		sig_comment = '' #str(table.cell_value(i, excelFormat["description"]).strip().replace('\n', ';'))
		canMsg[cur_msg_idx].setSignal(name = sig_name, meaning = sig_meaning, start_bit = sig_start_bit, length = sig_length, type = sig_type, factor = factor, offset = offset, rangefrom = rangefrom, rangeto = rangeto, init = init, invalid = invalid, comment = sig_comment)
	
		if (i+1) == nrows:	#一组数据组装完成
			#print("采集到第%d帧报文"%(cur_msg_idx))
			cur_msg_idx += 1
			break
		if table.cell(i+1,0).ctype != 0:
			#print("采集到第%d帧报文"%(cur_msg_idx))
			cur_msg_idx += 1
	print("find frame: %d"%cur_msg_idx)
	return canMsg[:cur_msg_idx]
	
def getMsgCycleTimeFromDbcString(src, msg):
	defTxCycleTime = 0
	for i in range(len(src)):
		if re.match("BA_DEF_DEF_  \"GenMsgCycleTime\"", src[i]):
			#print(lines[i].split())
			defTxCycleTime = int(src[i].split()[-1].rstrip(';'))
			break
	for i in range(len(src)):
		if re.match("BA_ \"GenMsgCycleTime\"", src[i]) and src[i].find(msg) >= 0:
			#print(lines[i].split())
			 return int(src[i].split()[-1].rstrip(';'))
	return defTxCycleTime

# 从DBC文件中导入CAN协议
def getCanFrameFromDbc(filename, module = ''):
	with open(filename, 'r') as fl:
		canMsg = []
		lines = fl.readlines()
		frameCnt = 0
		signalCnt = 0
		
		for idx in range(len(lines)):
			# 获取message
			if re.match("BO_ ", lines[idx]) and lines[idx].find("INDEPENDENT_SIG_MSG") < 0:
				if lines[idx+1].strip() == '':
					print("filter reserved message: %s"%lines[idx])
					continue
				frameCnt += 1
				canMsg.append(Frame())
				frame = lines[idx].split()
				type = 'x'
				if module != '':
					type = 's' if frame[4].find(module) >= 0 else 'r'

				period = getMsgCycleTimeFromDbcString(lines, frame[1])
				comment = ''
				for i in range(len(lines)):
					if lines[i].find("CM_ BO_")>=0 and lines[i].find(frame[1]) > 0:
						comment = ''.join(re.findall(".*\"(.*)\"", lines[i]))
						break
				
				#print("\n\nfind a frame:id=%x, name=%s, length=%d, transmiter=%s"%(int(frame[1]), frame[2].strip(":"), int(frame[3]), frame[4]))
				canMsg[-1].setFrame(name = frame[2].strip(":"), type = type, period=period, id = str(hex(int(frame[1]) & 0x1fffffff)), comment=comment, length = int(frame[3]))

				for tmp in range(idx+1, len(lines)):
					if lines[tmp].find("SG_") < 0:
						break
					signalCnt += 1
					signal = lines[tmp].split()
					#print(signal)
					sig_name = signal[1]
					sig_start_bit = int(signal[3][0:signal[3].find('|')])
					sig_length = int(''.join(re.findall(".*\|(.*)@.*", signal[3])))
					order = "inter" if signal[3][-2] == '0' else "motorlora"
					sig_type = "unsigned" if signal[3][-1] == '+' else "signed" 
					if signal[3][-1] == '-':
						for i in range(len(lines)):
							if re.match("SIG_VALTYPE", lines[i]):
								type_tmp = lines[i].split()
								if type_tmp[1] == frame[1] and type_tmp[2] == signal[1]:
									if type_tmp[4][0] == '1':
										sig_type = "float"
									else:
										sig_type = "double"
					factor = ''.join(re.findall("\((.*),.*", signal[4]))
					offset = ''.join(re.findall(".*,(.*)\)", signal[4]))
					rangefrom = ''.join(re.findall("\[(.*)\|.*", signal[5]))
					rangeto   = ''.join(re.findall(".*\|(.*)\]", signal[5]))
					init = 0
					unit = 'none' if len(signal[6]) <= 2 else signal[6][1:-1]
					sig_meaning = ''
					for i in range(len(lines)):
						if re.match("VAL_ ", lines[i]):
							type_tmp = lines[i].split()
							if type_tmp[1] == frame[1] and type_tmp[2] == signal[1]:
								sig_meaning = lines[i][(lines[i].find(type_tmp[2]) + len(type_tmp[2])):].strip().rstrip(';')
								break

					sig_comment = ''
					for i in range(len(lines)):
						if re.match("CM_ SG_", lines[i]):
							type_tmp = lines[i].split()
							if type_tmp[2] == frame[1] and type_tmp[3] == signal[1]:
								sig_comment = ''.join(re.findall(".*\"(.*)\"", lines[i]))
					#if sig_type.find("signed") >= 0:
					#	print("signal:name=%s, start_bit=%d, length=%d, order=%s, type=%s, factor=%s, offset=%s,rangefrom=%s,rangeto=%s,init=%d, unit=%s, comment=%s"%(sig_name, sig_start_bit, sig_length, order, sig_type, factor, offset, rangefrom, rangeto, init, unit, sig_comment))
					#else:
					#	print("signal:name=%s, start_bit=%d, length=%d, order=%s, type=%s, factor=%s, offset=%s,rangefrom=%s,rangeto=%s,init=%f, unit=%s, comment=%s"%(sig_name, sig_start_bit, sig_length, order, sig_type, factor, offset, rangefrom, rangeto, init, unit, sig_comment))
					canMsg[-1].setSignal(name=sig_name, start_bit=sig_start_bit,length=sig_length, type=sig_type, factor=factor, offset=offset, rangefrom=rangefrom, rangeto=rangeto, init=init, meaning=sig_meaning, comment=sig_comment)
		print("find frames:%d, with count of signal=%d"%(frameCnt, signalCnt))
		return canMsg
						



def InitFile(filename):
	with open(filename, 'w+') as fl:
		fl.write('')
		fl.flush()
		fl.close()
def WriteData2File(filename, data):
	with open(filename, 'a+') as fl:
		fl.write(data)
		fl.flush()
		fl.close()


man_help = '''
## CAN协议转C代码工具说明

+ 主要用途： 生成基于某个特定CAN协议的CAN报文结构体（基于C语言），方便后续程序的开发

+ 使用方法： `python3 produce_encode_can.py --flagfile=./flag.file`

    使用excel表协议时，表中需要有以下列

    | frame_name | frame_type | frame_id | period | frame_length | signal_name | start_bit | signal_length | signal_type | factor | offset | Range From | Range To | Initial | invalid | unit | value | description |
'''

if __name__ == '__main__':
	Flags(sys.argv)

	filename = Flags.output_file
	canMsg = []
	if Flags.proto_file.find('.xls') >= 0:
		print("get frames information from excel: file:%s, sheet_numb=%d"%(Flags.proto_file, Flags.sheet_numb))
		canMsg = getCanFrameFromExcel(Flags.proto_file, Flags.sheet_numb)
	elif Flags.proto_file.find('.dbc') >= 0:
		print("get frames information from dbc: %s, network node=%s"%(Flags.proto_file, Flags.node_name))
		canMsg = getCanFrameFromDbc(Flags.proto_file, Flags.node_name)
	else:
		print("unknow file format, exit")
		sys.exit()

	InitFile(filename)
	

	cans_frame_str = ''
	canr_frame_str = ''
	cans_list_body_str = ''
	cans_frame_list = []
	cans_cnt = 0
	print("deal can protocol...")
	for idx in range(len(canMsg)):
		#print("deal %d... frame id=%s\r"%(idx+1, canMsg[idx].id), end='')
		canMsg[idx].setFrameStructStr()
		frameStr = canMsg[idx].getFrameStructStr()
		if canMsg[idx].type == 's':
			cans_cnt += 1
			cans_frame_str += frameStr

			if frameStr.find("\nstruct"):
				test = frameStr.splitlines(False)
				testTmp = ''.join(test[2])
				testHead = testTmp[0:testTmp.find('{')].rstrip()
				cans_frame_list.append(testHead)
			cans_list_body_str += canMsg[idx].getSendFrameInfo()
		else:
			canr_frame_str += frameStr

	headStrTmp = Template(temp_string.fl_head_string)
	headStr = headStrTmp.substitute(CAN_CHANNEL=Flags.channel, PERIOD_TIME=Flags.circle_period, MACRO_CANSEND="#define NUM_OF_SEND_ID\t\t\t"+str(cans_cnt) + '\t//CAN发送数据组数')
	WriteData2File(filename, headStr)
	#WriteData2File(filename, temp_string.fl_head_string)

	if cans_frame_str != '':
		cans_comment='''
/**************************************** CAN send frame ****************************************/'''
		WriteData2File(filename, cans_comment)
		WriteData2File(filename, cans_frame_str)
	
	if canr_frame_str != '':
		canr_comment='''
/************************************* CAN receive frame *************************************/'''
		WriteData2File(filename, canr_comment)
		WriteData2File(filename, canr_frame_str)
	
	WriteData2File(filename, "\n// CAN发送列表\n")
	for idx in range(len(cans_frame_list)):
		strTmp = Template("${HEAD} ${BODY};\n")
		testHead = cans_frame_list[idx]
		testBody = testHead[testHead.find("struct ")+7:].rstrip()
		strTmp1 = strTmp.substitute(HEAD=testHead, BODY=testBody)
		WriteData2File(filename, strTmp1)

	send_frame_tmp = Template(temp_string.can_send_temp)
	send_frame_str = send_frame_tmp.substitute(FRAME_LIST=cans_list_body_str)
	WriteData2File(filename, send_frame_str)

	func_comment='''
	
/********************************** detected dataes process **********************************/
'''
	WriteData2File(filename, func_comment)
	WriteData2File(filename, temp_string.func_lds_temp)
	WriteData2File(filename, temp_string.func_vds_temp)
	WriteData2File(filename, temp_string.func_pds_temp)
	WriteData2File(filename, temp_string.func_tds_temp)
	WriteData2File(filename, temp_string.func_time_init_temp)
	if Flags.enable_receive:
		WriteData2File(filename, temp_string.func_can_rcv_temp)
		

	devInitTmp = Template(temp_string.func_dev_init_temp)
	loopbackStr = '' if Flags.enable_loopback else temp_string.func_dev_init_loopback_temp
	receiveStr = temp_string.func_dev_init_enablereceive_temp if Flags.enable_receive else temp_string.func_dev_init_disablereceive_temp
	sendSplitStr = temp_string.func_dev_init_send_split_temp if Flags.enable_sendSplit else ''

	devInitStr = devInitTmp.substitute(CAN_LOOPBACK=loopbackStr, CAN_RCV_INIT=receiveStr, CAN_SEND_SPLIT=sendSplitStr)

	WriteData2File(filename, devInitStr)
	#WriteData2File(filename, temp_string.func_dev_init_temp)
	
	print("\nfinish, create file: %s"%filename)
	sys.exit()
