from bs4 import BeautifulSoup
import urllib.request as req
import requests
from datetime import timedelta, datetime
from flask import Flask, render_template,request,redirect,flash,session,url_for,jsonify
from flask_pymongo import PyMongo
from flask_jwt_extended import *
from werkzeug.security import generate_password_hash, check_password_hash
import FinanceDataReader as fdr
#내가 만든 모듈
from basic import db_connect,only_code_made, time_format
from inquiry import stock_inquiry, rate_import
import portfolio as p
import chartcode as c
import COIN
import US
import db
import sys
import PWD

#로그 관리 
#TEST
import logging
logging.basicConfig(filename = "./logs/test.log", level = logging.DEBUG)
nowDATE = time_format()
pwd = PWD.pwd()
app = Flask(__name__)
#app.config.update(DEBUG = True, JWT_SECRET_KEY = "thisissecertkey" )
#jwt = JWTManager(app)
#app.config['JWT_COOKIE_SECURE'] = False # https를 통해서만 cookie가 갈 수 있는지 (production 에선 True)
#app.config['JWT_TOKEN_LOCATION'] = ['cookies']
#app.config['JWT_ACCESS_COOKIE_PATH'] = '/main' # access cookie를 보관할 url (Frontend 기준)
#app.config['JWT_REFRESH_COOKIE_PATH'] = '/main' # refresh cookie를 보관할 url (Frontend 기준)
#app.config['JWT_COOKIE_CSRF_PROTECT'] = True
app.config["MONGO_URI"] = "mongodb+srv://maeseok:"+pwd+"@finance.smjhg.mongodb.net/members?retryWrites=true&w=majority"
app.config["SECRET_KEY"] = "bvWjJlEvRqsOBPnu"
app.config["PERMANET_SESSION_LIFETIME"] = timedelta(minutes = 30)
mongo = PyMongo(app)
#대표 화면
@app.route("/main")
def home():  
    #이건 DB도 옮기자! CRON까지 이용하면 좋을듯
    #결국 이 함수때문에 늦음 -> 한계인가?
    coinRate,coinProfit,sp500Rate,sp500Profit,kospiRate,kospiProfit = db.inquiry_index()
    return render_template("index.html",kospiRate = kospiRate, sp500Rate = sp500Rate, kospiProfit = kospiProfit,sp500Profit = sp500Profit,
    coinRate = coinRate, coinProfit = coinProfit)

@app.route("/")
def main():
    return render_template("main.html")
@app.route("/new",methods=["GET","POST"])
def new():
    if request.method == "POST":
        #여기 입력되지 않은 값이나 비밀번호 일치 오류 등 js로 
        ID = request.form.get("id",type=str)
        pwd = request.form.get("pwd",type=str)
        pwd2 = request.form.get("pwd2",type=str)
        NICK = request.form.get("nick",type=str)
        if id=="" or pwd=="" or pwd2==""or NICK=="":
            flash("입력되지 않은 값이 있습니다.")
            return render_template("new.html") 
        if pwd!=pwd2:
            flash("비밀번호가 일치하지 않습니다.")
            return redirect(url_for("new"))
        members = mongo.db.members
        data = members.find_one({"id":ID})
        if data is not None:
            flash("아이디가 중복됩니다.")
            return redirect(url_for("new"))

        post={
            "id":ID,
            "password": generate_password_hash(pwd),
            "nickname":NICK,
            "logintime":"",
            "logincount":0,
        }

        members.insert_one(post)
        flash("회원가입이 완료되었습니다.")
        return redirect(url_for("login"))
    else:
        return render_template("new.html")

@app.route("/login",methods=['GET','POST'])
def login():
    if request.method == "POST":
        ID = request.form.get("id",type=str)
        pwd = request.form.get("pwd",type=str)
        members = mongo.db.members
        #members.create_index("id")
        data = members.find_one({"id":ID})
        if data is None:
            flash("회원정보가 없습니다.")
            return redirect(url_for("login"))
        else:
            if check_password_hash(data.get("password"),pwd):
                #access_token = create_access_token(identity = ID, expires_delta = False)
                #refresh_token = create_refresh_token(identity = ID)

                #resp = jsonify({'login' : True})

                # 서버에 저장
                #set_access_cookies(resp, access_token)
                #set_refresh_cookies(resp, refresh_token)

                session["ID"] = str(data.get("id"))
                session.permenent = True
                flash("로그인 성공!")
                return redirect(url_for("home"))
            else:
                flash("비밀번호가 일치하지 않습니다.")
                return redirect(url_for("login"))
    elif request.method == "GET":
        return render_template("login.html")
    else:
        return redirect(url_for("main"))
@app.route('/logout')
def logout():
    session.pop('ID', None)
    flash("로그아웃 성공!")
    return redirect('/main')
#포트폴리오 이용 설명
@app.route("/port_explain")
def port_explain():
    return render_template("port_explain.html")
#시세 조회
@app.route("/inquiry")
def inquiry():
    return render_template("inquiry.html")
#코인 시세 검색
@app.route("/inquiry/coin")
def coininquiry():
    return render_template("inquiryCoin.html")
#코인 시세 결과
@app.route("/inquiry/coinrate")
def coinreturn():
    #try:
    moneyvalue = request.args.get('moneyValue')
    coinname = request.args.get('coinname')
    if(moneyvalue== "KRW"):
        df_coin,rate= COIN.coin_connect(moneyvalue,coinname,500)
        coinrate = COIN.coin_rate(moneyvalue,coinname,df_coin,rate)
    elif(moneyvalue == "USD"):
        ticker,rate = COIN.usd_connect(coinname)
        df_coin = COIN.get_df_binance(ticker, "1d")
        coinrate = COIN.coin_rate(moneyvalue, coinname, df_coin,rate)
    COIN.basic_chart(df_coin, coinname,moneyvalue)
    COIN.real_chart(df_coin,coinname)
    #except:
        #return redirect("/")
    return render_template("inquiryCoinrate.html",searchingBy=coinname,stockRate=coinrate)
#포트폴리오 
@app.route("/portfolio")
def portfolio():
    try:
        if(session['ID']):
            return render_template("portfolio.html")
    except:
        flash("로그인을 먼저 해주세요.")
        return render_template("login.html")
#코스피 코스닥 오늘의 종목 검색
@app.route("/inquiry/search")
def inquirySearch():
    return render_template("inquirySearch.html")
#코스피 코스닥 오늘의 시세 출력
@app.route("/inquiry/todayrate")
def inquiryTodayrate():
    try:
        company = request.args.get('company')
        date = request.args.get('date')
        df_krx = c.KRX_connect()
        stock_rate,symbol,df= c.KRX_rate(df_krx,company,date)
        df.reset_index(inplace=True)
        #chart img
        US.basic_chart(df,company)
        #chart html
        US.real_chart(df,company)
    except:
        return redirect("/")
    return render_template("inquiryTodayrate.html",searchingBy=company,stockRate=stock_rate)

#나스닥 오늘의 종목 검색
@app.route("/inquiry/nasdaq")
def NasdaqSearch():
    return render_template("inquiryNasdaq.html")
#나스닥 오늘의 시세 출력
@app.route("/inquiry/nasdaqrate")
def NasdaqRate():
    try:
        company = request.args.get('company')
        date = request.args.get('date')
        df_nasdaq = US.NASDAQ_connect()
        stock_rate,symbol = US.NASDAQ_rate(df_nasdaq,company)
        df = US.df_made(symbol,date)
        #chart img
        US.basic_chart(df,company)
        #chart html
        US.real_chart(df,company)
    except:
        return redirect("/")
    return render_template("inquiryNasdaqrate.html",searchingBy=company,stockRate=stock_rate)

#뉴욕 증권거래소 오늘의 종목 검색
@app.route("/inquiry/nyse")
def NyseSearch():
    return render_template("inquiryNyse.html")
#뉴욕 증권거래소 오늘의 시세 출력
@app.route("/inquiry/nyserate")
def NyseRate():
    #try:
    company = request.args.get('company')
    date = request.args.get('date')
    df_nyse = US.NYSE_connect()
    stock_rate,symbol = US.NYSE_rate(df_nyse,company)
    df = US.df_made(symbol,date)
    #chart img
    US.basic_chart(df,company)
    #chart html
    US.real_chart(df,company)
    #except:
        #return redirect("/")
    return render_template("inquiryNyserate.html",searchingBy=company,stockRate=stock_rate)

#아맥스 종목 검색
@app.route("/inquiry/amex")
def AmexSearch():
    return render_template("inquiryAmex.html")
#아맥스 오늘의 시세 출력
@app.route("/inquiry/amexrate")
def AmexRate():
    try:
        company = request.args.get('company')
        date = request.args.get('date')
        df_amex = US.AMEX_connect()
        stock_rate,symbol = US.AMEX_rate(df_amex,company)
        df = US.df_made(symbol,date)
        #chart img
        US.basic_chart(df,company)
        #chart html
        US.real_chart(df,company)
    except:
        return redirect("/")
    return render_template("inquiryAmexrate.html",searchingBy=company,stockRate=stock_rate)

#미국 ETF 종목 검색
@app.route("/inquiry/etfUS")
def EtfUS():
    return render_template("inquiryEtfUS.html")

#미국 ETF 오늘의 시세 출력
@app.route("/inquiry/etfUSrate")
def EtfUSrate():
    try:
        company = request.args.get('company')
        date = request.args.get('date')
        name = ""
        for i in range(len(company)):
            if company[i] == "[":
                name = company[:i]
        df_etfus = US.ETFUS_connect()
        stock_rate,symbol = US.ETFUS_rate(df_etfus,name,company)
        df = US.df_made(symbol,date)
        #chart img
        US.basic_chart(df,name)
        #chart html
        US.real_chart(df,name)
    except:
        return redirect("/")
    return render_template("inquiryEtfUSrate.html",searchingBy=name,stockRate=stock_rate)

#고급 차트 출력
@app.route("/chart")
def stockchart():
    return render_template("chart.html")

#종목 수익률 검색
@app.route("/inquiry/return")
def inquiryReturn():
    return render_template("inquiryReturn.html")

#종목 수익률 출력
@app.route("/inquiry/stock_return")
def stock_return():
    try:
        stocks = request.args.get('stocks')
        firstdate = request.args.get('purchase_date')
        lastdate = request.args.get('sale_date')
        df_krx = c.KRX_connect()
        KRX = c.KRX_yield(df_krx, stocks, firstdate, lastdate)
        return render_template("inquiryStock_return.html",KRX=KRX)
    except:
        return redirect("/")

#종목 매수 정보 입력
@app.route("/portfolio/buy")
def portfolioBuy():
    try:
        if(session['ID']):
            return render_template("portfolioBuy.html")
    except:
        flash("로그인을 먼저 해주세요.")
        return render_template("login.html")

#매수 완료 처리
@app.route("/portfolio/buy_return")
def portfolioBuy_return():
    if(session['ID']):
        pass
    else:
        flash("로그인을 먼저 해주세요.")
        return render_template("login.html")
    usersession = session['ID']
    name = request.args.get('name')
    moneyvalue = request.args.get('moneyValue')
    price = int(request.args.get('price'))
    number = int(request.args.get('number'))
    symbol=""
    datacheck=""
    checkCode="0"
    try:
        df_krx = c.KRX_connect()
        symbol = df_krx[df_krx.Name==name].Symbol.values[0].strip()
    except:
        flash("종목명을 확인해주세요.")
        return redirect("/portfolio/buy")
    #db 관련 코드 시작
    user = mongo.db.userdata
    data = user.find({
    "$and" : [{
                 "Id" : usersession
              },
              {
                  "Name":name
              }]
})
    for i in data:
        datacheck = i.get("_id")
        firstnum = int(i.get("Number"))
        firstprice = int(i.get("Price"))
    #데이터가 있다는 건 추가 매수라는 뜻 -> 값을 수정해야함
    if(datacheck):
        if(symbol):
            user.update_one({
            "_id": datacheck
            },
            {"$set":
            {
            "Price" : (firstprice*firstnum+price*number)/(firstnum+number),
            "Number": firstnum+number
            }
            }
            )
            checkCode ="1"
            pass
    #신규 매수라는 뜻 -> 값을 추가해야함
    else:
        if(symbol):
            post ={"Id":usersession,"Name":name,"Price":price,"Number":number}
            user.insert_one(post)
            checkCode ="2"

    path="/nomadcoders/boot/DB/check.txt"
    file = open(path, 'a')
    #global checkCode
    file.write(checkCode)
    file.close()
    return render_template("portfolioBuy_return.html")


#종목 매수 완료
@app.route("/portfolio/buyreturn")
def BuyReturn():
    try:
        if(session['ID']):
            pass
        else:
            flash("로그인을 먼저 해주세요.")
            return render_template("login.html")
        path="/nomadcoders/boot/DB/check.txt"
        file = open(path, 'r')
        Check=int(file.read())
        file.close()
        file2 = open(path, 'w')
        file2.close()
        if(Check!=0):
            pass
        else:
            return redirect("/portfolio")
    except:
        return redirect("/portfolio")
    return render_template("portfolioBuyReturn.html",check=Check)


#여기서부터 다시 해야함
#종목 매도 정보 입력
@app.route("/portfolio/sell")
def portfolioSell():
    try:
        if(session['ID']):
            return render_template("portfolioSell.html")
    except:
        flash("로그인을 먼저 해주세요.")
        return render_template("login.html")

#종목 매도 처리
@app.route("/portfolio/sell_return")
def portfolioSell_return():
    try:
        try:
            if(session['ID']):
                pass
        except:
            flash("로그인을 먼저 해주세요.")
            return render_template("login.html")
        usersession = session['ID']
        sellname = request.args.get('name2')
        sellprice = int(request.args.get('price2'))
        sellnumber = int(request.args.get('number2'))
        moneyvalue = request.args.get('moneyValue')
        symbol = ""
        try:
            df_krx = c.KRX_connect()
            symbol = df_krx[df_krx.Name==sellname].Symbol.values[0].strip()
        except:
            flash("종목명을 확인해주세요.")
            return redirect("/portfolio/sell")
        datacheck=""
        user = mongo.db.userdata
        sellprofit = mongo.db.profit
        data = user.find({
        "$and" : [{
                    "Id" : usersession
                },
                {
                    "Name":sellname
                }]
        })
        for i in data:
            datacheck = i.get("_id")
            firstnum = int(i.get("Number"))
            firstprice = int(i.get("Price"))
        check = "0"
        checkcode = ""
        if (symbol):
            if(datacheck):
                #매도량이 매수량보다 많은지 확인
                if(firstnum < sellnumber):
                    checkcode = 0
                else:
                    checkcode = 1
            else:
                flash("종목명을 확인하세요.")
                return redirect("/portfolio/sell")
            #정상
            if(checkcode == 1):
                remainprice = sellprice - firstprice
                profit = (sellprice - firstprice) / firstprice*100
                realprofit = remainprice * sellnumber
                #매도한 정보 저장 - 조회 때 number 0 이면 출력 안하는 느낌 
                user.update_one({
                "_id": datacheck
                },
                {"$set":
                {
                "Number": firstnum - sellnumber
                }
                }
                )
                #수익률 정보 저장 - 단위는 저장 안해서 매도수익 조회 때 해야함
                post ={"Id":usersession,"SellName":sellname,"Firstprice":firstprice,"Lastprice":sellprice,
                "Sellnumber":sellnumber,"Profit":profit,"Realprofit":realprofit}
                sellprofit.insert_one(post)
                #p.profit_and_loss(sellname, saveprice, sellprice, remainprice, sellnumber)
                check ="1"
            #매도량이 매수량을 넘음
            else:
                #추가되어서 넘친 매도량 삭제
                flash("매도 수량을 확인하세요.")
                check="2"
                return redirect("/portfolio/sell")
        path="/nomadcoders/boot/DB/check.txt"
        file = open(path, 'a')
        file.write(check)
        file.close()
    except:
        flash("입력한 값을 확인하세요.")
        return redirect("/portfolio/sell")
    return render_template("portfolioSell_return.html")

#종목 매도 완료
@app.route("/portfolio/sellreturn")
def portfolioSellReturn():
    try:
        try:
            if(session['ID']):
                pass
        except:
            flash("로그인을 먼저 해주세요.")
            return render_template("login.html")
        path="/nomadcoders/boot/DB/check.txt"
        file = open(path, 'r')
        Check=int(file.read())
        file.close()
        file2 = open(path, 'w')
        file2.close()
        print(Check)
        if(Check!=0):
            pass
        else:
            return redirect("/portfolio")
    except:
        return redirect("/portfolio")
    return render_template("portfolioSellReturn.html",checkcode = Check)

#포트폴리오 출력
@app.route("/portfolio/inquiry")
def portfolioInquiry():
    #초기 리스트 생성
    #try:
        try:
            if(session['ID']):
                pass
        except:
            flash("로그인을 먼저 해주세요.")
            return render_template("login.html")
        Buyinfor = []
        df_krx = c.KRX_connect()
        usersession = session['ID']
        user = mongo.db.userdata
        data = user.find({"Id":usersession})
        for i in data:
            Name = i.get("Name")
            Firstrate = i.get("Price")
            Number = i.get("Number")
            symbol = df_krx[df_krx.Name==Name].Symbol.values[0].strip()
            date=COIN.time_format()
            df_rate = fdr.DataReader(symbol,date)
            print(df_rate)
            Lastrate = df_rate['Close'].values[0]
            print(Lastrate)
            rate_gap = int(Lastrate) - int(Firstrate)
            Rateprofit= rate_gap /int(Firstrate)*100
            present_profit = rate_gap * int(Number)
            Buyinfor.append(Name) #매수 종목
            Buyinfor.append(Firstrate) #평단가
            Buyinfor.append(Lastrate)  #현재가
            Buyinfor.append(Number) #남은 수량
            Buyinfor.append(Rateprofit) #현재 수익률
            Buyinfor.append(present_profit) #현재 수익
        portfolio_len =len(Buyinfor)
        #global p
        #Buyitem= []
        #get_code = []
        #get_profit = []
        #get_presentrate = []
        #get_presentprofit = []
        #Buyremain=[]
        #sell_already=[]
        #ptotal=[]
        #ltotal=[]
        #last_total=0
        #present_total=0
        #longline = "\n"
        #매수 정보 불러옴
        #Buyinfor = p.buy_open()
        #Sellinfor = p.sell_open()
        #Size = len(Buyinfor) / 3
        #for i in range(0,int(Size)):
            #매수 종목을 리스트에 저장
        #    Buyitem.append(Buyinfor[3*i])
        #for i in range(0,len(Buyitem)):
        #    for j in range(0,len(Buyinfor)):
                #종목 이름이 들어있는 항목의 위치를 찾음
        #        if(Buyitem[i] == Buyinfor[j]):
                    #매도한 내용이 있는지 확인
        #            if(len(Sellinfor) != 0):
        #                for s in range(0,len(Sellinfor)):
        #                    if(Buyinfor[j] == Sellinfor[s]):
        #                        if(Sellinfor[s] not in sell_already):
                                    #해당 종목의 매도량을 저장함
        #                            stocknumber = p.stock_item_open(Buyitem[i])
                                    #현재 남은 수량을 저장함
        #                           Buyremain = int(Buyinfor[j+2]) - stocknumber
                                    #리스트에 최신화(리스트를 이용하여 출력할 것이기 때문이다.)
        #                            Buyinfor[j+2] = Buyremain
        #                            sell_already.append(Sellinfor[s])
                                    #코드만 불러옴
        #                        else:
        #                            pass
        #                    else:
        #                        Buyremain = Buyinfor[j+2]
        #            else:
                        #매도 내용이 없으면 현재 수량을 남은 수량으로 저장
        #                Buyremain = Buyinfor[j+2]
                    #최종적으로 종목을 출력 형식에 맞게 값을 변형시킴
        #            df_krx = c.KRX_connect()
        #            get_code = df_krx[df_krx.Name==Buyitem[i]].Symbol.values[0].strip()  
        #            get_profit, get_presentrate, get_presentprofit,get_ptotal,get_ltotal = p.present_rate(get_code,Buyitem[i],Buyinfor[j+1],Buyremain) 
        #            ptotal.append(get_ptotal)
        #            ltotal.append(get_ltotal)
        #            Buyinfor.insert(j+2,get_presentrate)
        #            Buyinfor.insert(j+3,get_profit)
        #            Buyinfor.insert(j+5,get_presentprofit)
        #            Buyinfor.insert(j+6,longline)
        #        else:
        #            pass
        #for l in range(0, len(Buyinfor)):
        #    if(Buyinfor[l] == 0):
                #만약 남은 수량이 0이라면 해당 정보가 출력되지 않게 삭제함
        #        del Buyinfor[l-4:l+3]
        #        break
        #    else:
        #        pass

        #입력된 내용을 형식적으로 다듬는 과정
        #for k in range(0,len(Buyinfor)):
        #    if(k%7 == 1 ):
        #        average_rate = Buyinfor[k]
        #        get_average = format(int(average_rate),',')
        #        average = "평단가 : "+ get_average+"원"
        #        Buyinfor[k] = average
        #    elif(k%7 == 4):
        #        amount = Buyinfor[k]
        #        get_amount = format(int(amount),',')
        #        stock_amount = "수량 : " + get_amount+"주"
        #        Buyinfor[k] = stock_amount
        #    else:
        """        pass
        #총합 값 계산
        for n in range(0,len(ltotal)):
            last_total += ltotal[n] 
            present_total += ptotal[n] 
        #형식에 맞게 값 저장
        get_latotal = format(last_total,',')
        get_prtotal = format(present_total,',')
        if(present_total-last_total== 0):
            Buyinfor.append("구매 총합 : "+get_latotal+"원")
            Buyinfor.append("현재 총합 : "+get_prtotal+"원")
        else:
            total_profit = (present_total-last_total)/last_total*100
            Buyinfor.append("구매 총합 : "+get_latotal+"원")
            Buyinfor.append("현재 총합 : "+get_prtotal+"원")
            Buyinfor.append("총 수익률 : "+"{:0,.2f}".format(total_profit)+"%")
        portfolio_len =len(Buyinfor)"""
        return render_template("portfolioInquiry.html",portfolio=Buyinfor,portfolio_len=portfolio_len)
    #except:
        #return render_template("portfolio.html")

#매도 수익 출력
@app.route("/portfolio/return")
def portfolioReturn():
    #try:
    if(session['ID']):
        pass
    #except:
    #    flash("로그인을 먼저 해주세요.")
    #    return render_template("login.html")
    PLcollect = []
    sellprofit = mongo.db.profit
    Session = session['ID']
    result = sellprofit.find({"Id":Session})
    for i in result:
        #원화 달러 같은 통화 개념 구축해야하고, 수익률과 가격 format으로 자릿수와 , 해야함 {0:,.2f}
        PLcollect.append(i.get("SellName"))
        PLcollect.append(i.get("Firstprice"))
        PLcollect.append(i.get("Lastprice"))
        PLcollect.append(i.get("Sellnumber"))
        PLcollect.append(i.get("Profit"))
        PLcollect.append(i.get("Realprofit"))
    length = len(PLcollect)
    return render_template("/portfolioReturn.html",PLcollect=PLcollect,len=length)


#포트폴리오 초기화 여부 확인
@app.route("/portfolio/init")
def portfolioInit():
    try:
        if(session['ID']):
            return render_template("/portfolioInit.html")
    except:
        flash("로그인을 먼저 해주세요.")
        return render_template("login.html")

#포트폴리오 초기화
@app.route("/portfolio/init_return")
def portfolioInit_return():
    try:
        if(session['ID']):
            pass
        initialize = request.args.get('initialize')
        if(initialize=="초기화"):
            stock_item = p.buy_open()
            p.portfolio_initialize(stock_item)
        else:
            pass
        return render_template("/portfolioInit_return.html",initialize=initialize)
    except:
            flash("로그인을 먼저 해주세요.")
            return render_template("login.html")


app.run(host="0.0.0.0", debug=True)