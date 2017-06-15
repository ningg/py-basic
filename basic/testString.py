# -*- coding: utf-8 -*-

import datetime

from geopy.distance import vincenty

# 日期常量
DATETIME_PATTERN = "%Y-%m-%d %H:%M:%S"
# 经纬度字典中, 经度和纬度的 key
LNG_KEY = "lng"
LAT_KEY = "lat"
# 骑行轨迹, 重算结果字典中内容
NEW_TOTAL_DISTANCE = "totalDistance"
NEW_TRACK_RESULT = "trackResult"
NEW_CARBON = "carbon"
START_LNG_LAT_DICT = "STARTPOSITION"
END_LNG_LAT_DICT = "ENDPOSITION"


# 字符串转换为日期
def str2Datetime(datetimeStr):
    return datetime.datetime.strptime(datetimeStr, DATETIME_PATTERN)


# 日期转换为字符串
def datetime2Str(oriDatetime):
    return oriDatetime.strftime(DATETIME_PATTERN)


# 时间戳转换为日期
def timestamp2Datetime(timestamp):
    return datetime.datetime.fromtimestamp(int(timestamp) / 1000)


# 根据经纬度, 构造dict
def getDictOfLngLat(lng, lat):
    lngLatDict = {}
    lngLatDict[LNG_KEY] = lng
    lngLatDict[LAT_KEY] = lat
    return lngLatDict


# 根据经纬度,计算距离(m)
def calculateDistanceByLngAndLat(firstLngLatDict, secondLngLatDict):
    # 单位: m
    return vincenty((firstLngLatDict[LAT_KEY], firstLngLatDict[LNG_KEY]),
                    (secondLngLatDict[LAT_KEY], secondLngLatDict[LNG_KEY])).kilometers * 1000.0


# 重算轨迹数据
def filterTrackTime(trackTime, orderStartTime, orderEndTime):
    resultDict = {}
    effectiveTrackDictList = []
    totalTrackDictList = []
    for singlePoint in trackTime.split("#"):
        # 过滤: 空行
        if singlePoint:
            # 获取「经纬度」和「时间」
            lngLatTimestamp = singlePoint.split(";")

            # 如果出现异常数据,直接跳过
            # 1. 经纬度和时间戳, 缺少一个数据, 跳过当前数据
            if len(lngLatTimestamp) != 2:
                continue
            # 2. 经纬度, 缺少精度或纬度, 跳过当前数据
            lngLat = lngLatTimestamp[0].split(",")
            if len(lngLat) != 2:
                continue
            # 3. 经纬度, 数据异常(经纬度 0 点), 跳过当前数据(lng, lat)=(经度,纬度)
            lng = float(lngLat[0])
            lat = float(lngLat[1])
            if (lng == 0 and lat == 0) or ((lng > -0.1 and lng < 0.1) and (lat > -0.1 and lat < 0.1)) or lng > 180 or lng < -180 or lat > 90 or lat < -90:
                continue

            # 保留全量经纬度(已经初步过滤)
            currLngLatDict = getDictOfLngLat(lng, lat)
            totalTrackDictList.append(currLngLatDict)

            # 截取有效的经纬度: 时间戳,在订单的「起始时间」和「结束时间」范围内
            currDatetime = timestamp2Datetime(lngLatTimestamp[1])
            if orderStartTime <= currDatetime and currDatetime <= orderEndTime:
                effectiveTrackDictList.append(currLngLatDict)

    # print "totalTrackDictList : %s" % str(totalTrackDictList)
    # print "effectiveTrackDictList : %s" % str(effectiveTrackDictList)

    # 根据骑行经纬度, 重新计算:
    # 1. 骑行距离
    totalDistance = 0
    firstLngLatDict = {}
    secondLngLatDict = {}
    # 2. 骑行轨迹
    trackResult = ""
    for singleDict in effectiveTrackDictList:
        trackResult = trackResult + "#" + str(singleDict[LNG_KEY]) + "," + str(singleDict[LAT_KEY])
        # 第一个经纬度点为空
        if not firstLngLatDict:
            firstLngLatDict = singleDict
            continue
        else:
            secondLngLatDict = singleDict
            totalDistance = totalDistance + calculateDistanceByLngAndLat(firstLngLatDict, secondLngLatDict)
            firstLngLatDict = secondLngLatDict
    # 兜底逻辑:
    # 1. 骑行距离: 重算的骑行距离, 仍为 0, 则, 使用(时间mins x 180 m/min, 时间 s x 3 m/s) 作为距离估算
    if totalDistance == 0:
        totalDistance = (orderEndTime - orderStartTime).seconds * 3

    # 3. 根据「骑行距离」,计算「碳排放量」: distance/1000 * 0.12
    carbon = (totalDistance / 1000) * 0.12

    # 4. 订单的「开始经纬度」和「结束经纬度」
    startPosition = {}
    endPosition = {}
    if effectiveTrackDictList:
        startPosition = effectiveTrackDictList[0]
        startPosition = effectiveTrackDictList[-1]
    # 兜底逻辑: 「开始经纬度」和「结束经纬度」
    if totalTrackDictList:
        # 检查: 「起始经纬度」和「结束经纬度」,距离不能超过> 100km
        if calculateDistanceByLngAndLat(totalTrackDictList[0], totalTrackDictList[-1]) <= 100000:
            if not startPosition:
                startPosition = totalTrackDictList[0]
            if not endPosition:
                endPosition = totalTrackDictList[-1]

    resultDict[NEW_TOTAL_DISTANCE] = totalDistance
    resultDict[NEW_TRACK_RESULT] = trackResult
    resultDict[NEW_CARBON] = carbon
    resultDict[START_LNG_LAT_DICT] = startPosition
    resultDict[END_LNG_LAT_DICT] = endPosition

    return resultDict


if __name__ == "__main__":
    trackTime = "#4.9E-324,4.9E-324;1490613254643#116.293752,39.857372;1490613264107#116.293868,39.85738;1490613269107#116.293891,39.857311;1490613274103#116.293866,39.857237;1490613279106#116.293825,39.857136;1490613284108#116.293768,39.857067;1490613289111#116.293744,39.856968;1490613294108#116.293676,39.85681;1490613299110#116.29365,39.856655;1490613304111#116.29373,39.856516;1490613309111#116.293703,39.856359;1490613314114#116.293667,39.856217;1490613319128#116.293717,39.856088;1490613324118#116.293725,39.855937;1490613329125#116.293753,39.855773;1490613334118#116.293729,39.855611;1490613339213#116.29369,39.855476;1490613344220#116.293608,39.855352;1490613349246#116.293522,39.855307;1490613354251#116.293394,39.85535;1490613359240#116.293269,39.855356;1490613364136#116.293124,39.855369;1490613369261#116.292947,39.855335;1490613374226#116.292749,39.85534;1490613379241#116.292628,39.855224;1490613384260#116.292444,39.855227;1490613389236#116.292263,39.855286;1490613394144#116.292039,39.855275;1490613399253#116.291783,39.855286;1490613404275#116.291581,39.855293;1490613409268#116.291457,39.855259;1490613414236#116.29133,39.855233;1490613419153#116.29116,39.85518;1490613424152#116.290988,39.855178;1490613429257#116.290806,39.855166;1490613434155#116.290623,39.855151;1490613439156#116.2904,39.855147;1490613444161#116.290227,39.855187;1490613449268#116.289995,39.855126;1490613454293#116.289835,39.855216;1490613459268#116.289683,39.855239;1490613464276#116.289518,39.855214;1490613469268#116.289354,39.855203;1490613474319#116.289197,39.855245;1490613479290#116.289036,39.855313;1490613484277#116.288884,39.855344;1490613489281#116.288771,39.855331;1490613494284#116.288625,39.855459;1490613499291#116.288453,39.855448;1490613504179#116.288287,39.855439;1490613509298#116.288131,39.855419;1490613514292#116.287947,39.855383;1490613519300#116.287804,39.855369;1490613524312#116.287664,39.85538;1490613529295#116.287435,39.855295;1490613534192#116.287262,39.85528;1490613539306#116.287107,39.855295;1490613544317#116.286934,39.855264;1490613549327#116.286772,39.855243;1490613554322#116.286566,39.855238;1490613559313#116.286399,39.855204;1490613564323#116.28627,39.855062;1490613569202#116.286217,39.85494;1490613574330#116.286157,39.854818;1490613579339#116.286128,39.854687;1490613584278#116.286079,39.854561;1490613589349#116.286033,39.854453;1490613594351#116.286003,39.854368;1490613599455#116.285977,39.854253;1490613604331#116.285945,39.854092;1490613609460#116.286002,39.85399;1490613614215#116.286015,39.853823;1490613619324#116.285929,39.853541;1490613624328#116.285901,39.853404;1490613629331#116.28597,39.853376;1490613634218#116.286026,39.85326;1490613639222#116.28599,39.853161;1490613644229#116.285939,39.852985;1490613649365#116.285917,39.852753;1490613654373#116.285954,39.852666;1490613659350#116.285948,39.852526;1490613664349#116.285994,39.852402;1490613669356#116.286019,39.852229;1490613674231#116.286045,39.852045;1490613679230#116.286091,39.851875;1490613684372#116.286096,39.85166;1490613689369#116.286108,39.851446;1490613694360#116.286077,39.851305;1490613699367#116.286039,39.851107;1490613704378#116.286051,39.851076;1490613709249#116.28612,39.850945;1490613714335#116.28616,39.850726;1490613719366#116.286191,39.850558;1490613724367#116.286149,39.850369;1490613729256#116.286182,39.850182;1490613734383#116.286245,39.850058;1490613739385#116.286238,39.84999;1490613744381#116.286254,39.849814;1490613749258#116.286322,39.849694;1490613754258#116.286349,39.849574;1490613759257#116.286354,39.84951;1490613764424#116.286278,39.849317;1490613769269#116.286216,39.849168;1490613774267#116.286253,39.848976;1490613779267#116.286289,39.848866;1490613784271#116.286328,39.848739;1490613789367#116.286313,39.848568;1490613794271#116.286334,39.84848;1490613799418#116.28637,39.848416;1490613804268#116.286206,39.848312;1490613809361#116.28624,39.848084;1490613814273#116.286286,39.848062;1490613819274#116.286243,39.84798;1490613824363#116.286187,39.847942;1490613829285#116.286042,39.84784;1490613834417#116.285937,39.847837;1490613839281#116.285857,39.847816;1490613844366#116.285776,39.847776;1490613849285#116.285734,39.847783;1490613854286#116.285754,39.847821;1490613859282#116.285754,39.847827;1490613864386#116.285757,39.847823;1490613899376#116.285762,39.84772;1490613904464#116.285816,39.847718;1490613909400#116.285836,39.847705;1490613914394#116.285857,39.847686;1490613919393#116.285832,39.847665;1490613924397#116.285827,39.847664;1490613929392#116.285809,39.847658;1490613934623#116.285805,39.847661;1490613959307"
    trackTime = "#4.9E-324,4.9E-324;1490613254643"
    orderStartTime = str2Datetime("2017-03-27 19:14:06")
    orderEndTime = str2Datetime("2017-03-27 19:24:24")
    # 过滤原始骑行轨迹
    filterResult = filterTrackTime(trackTime, orderStartTime, orderEndTime)

    print "totalDistance: " + str(filterResult[NEW_TOTAL_DISTANCE])
    print "trackResult: " + str(filterResult[NEW_TRACK_RESULT])
    print "carbon: " + str(filterResult[NEW_CARBON])
    print "startPosition: " + str(filterResult[START_LNG_LAT_DICT])
    print "endPosition: " + str(filterResult[END_LNG_LAT_DICT])
