#!/usr/bin




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
		} bits;
		$FMT_TYPE vals;
	} B${START_BYTE}_${END_BYTE};'''

cb_frame_tmp = '''
struct can${RDWR}_id0x${CANID} {$FRAME_BODY	
}__attribute__((packed));
'''



fl_head_string = '''// Copyright (C) 2019 - Minieye INC.

#include <stdio.h>
#include <sys/time.h>
#include <unistd.h>

#include <sys/timerfd.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <linux/can.h>
#include <linux/can/raw.h>
#include <net/if.h>

#include <errno.h>
#include <linux/can/error.h>

#include "gflags/gflags.h"
#include "unified_process_rsp.h"


#define PERIOD_SLEEP_MS		50		//每次循环睡眠50ms
#define CAN_DEVICE			"can0"	// 根据实际产品定义CAN通道


#define min(x, y)			((x) > (y) ? (y) : (x))		// 取较小值
#define max(x, y)			((x) > (y) ? (x) : (y))		// 取较大值
#define mid(val, x, y)		(max(min((val), (y)), (x)))	// 取中间值


// declare gflag below
DECLARE_double(ldw_speed_thresh);


'''

func_lds_temp = '''
void do_lane_detect_rsp(struct LaneDetectRsp_all *lds) {
    static long long int time_base = 0;
    struct timeval tv;
    gettimeofday(&tv, NULL);
    LOG_LDS("%lld|frame_id:%u\n",
            (tv.tv_sec*1000 + tv.tv_usec/1000) - time_base,
                lds->rsp.frame_id);
    time_base = tv.tv_sec*1000 + tv.tv_usec/1000;
	
	char timestr[30];
	struct tm tm = *localtime(&tv.tv_sec);
	strftime(timestr, 29, "%Y-%m-%d %H:%M:%S", &tm);
	LOG_LDS("(%s.%lu):\n", timestr, tv.tv_usec);

	if (lds == NULL)
		return;
	
	// TODO

	for (size_t i = 0; i < lds->rsp.lanelines.size(); i++)
	{
		// TODO
	}

	// TODO

}
'''

func_vds_temp = '''
void do_vehicle_detect_rsp(struct VehicleDetectRsp_all *vds) {
	static long long int time_base = 0;
	struct timeval tv;
	gettimeofday(&tv, NULL);
	LOG_VDS("%lld|frame_id:%u\n",
	        (tv.tv_sec*1000 + tv.tv_usec/1000) - time_base,
	            vds->frame_id);
	time_base = tv.tv_sec*1000 + tv.tv_usec/1000;

	if (vds == NULL)
	{
		LOG_VDS("input ptr invalid\n");
		return;
	}
	
	// TODO
	
	for (size_t idx = 0; idx < vds->rsp.dets.size(); idx++)
	{
		// TODO
	}

	// TODO
	
}
'''

func_pds_temp = '''
void do_people_detect_rsp(struct PeopleDetectRsp_all *pds) {
	static long long int time_base = 0;
	struct timeval tv;
	gettimeofday(&tv, NULL);
	LOG_PDS("%lld|frame_id:%lld\n",
		    (tv.tv_sec*1000 + tv.tv_usec/1000) - time_base,
		        rsp->processed_frame_id);
	time_base = tv.tv_sec*1000 + tv.tv_usec/1000;

	struct tm tm = *localtime(&tv.tv_sec);
	char timestr[30];		
	strftime(timestr, 29, "%Y-%m-%d %H:%M:%S", &tm);
	LOG_PDS("(%s.%03ld)\n", timestr, tv.tv_usec/1000); 

	if (pds == NULL)
	{
		LOG_PDS("input ptr invalid\n");
		return;
	}

	// TODO

	for (size_t idx = 0; idx < pds->rsp.pedestrians.size(); idx++)
	{
		// TODO

	}
	
	// TODO

}
'''


func_tds_temp = '''
void do_tsr_detect_rsp(struct TsrDetectRsp_all *tds) {
	static long long int time_base = 0;
	struct timeval tv;
	gettimeofday(&tv, NULL);

	LOG_TDS("%lld|frame_id:%lld\n",
			(tv.tv_sec*1000 + tv.tv_usec/1000) - time_base, frame_id);
	time_base = tv.tv_sec*1000 + tv.tv_usec/1000;

	struct tm tm = *localtime(&tv.tv_sec);
	char timestr[30];		
	strftime(timestr, 29, "%Y-%m-%d %H:%M:%S", &tm);
	LOG_TDS("(%s.%03ld)\n", timestr, tv.tv_usec / 1000);

	if (tds == NULL)
	{
		LOG_TDS("input ptr invalid\n");
		return;
	}

	// TODO

	for (size_t idx = 0; idx < tds->rsp.tsr_dets.size(); idx++)
	{
		// TODO
	}

	// TODO

}
'''


