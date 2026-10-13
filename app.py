import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title='Murat Hoca | Kripto Radar', page_icon='📡', layout='wide')
BASE='https://www.binance.tr'
API1='https://api.binance.me/api/v1/klines'
API3='https://cloudme-tr.2meta.app/api/v1/klines'
HEADERS={'User-Agent':'MuratKriptoRadar/0.1'}

def get_json(url,params=None):
    r=requests.get(url,params=params,headers=HEADERS,timeout=12)
    r.raise_for_status()
    x=r.json()
    if isinstance(x,dict) and x.get('code',0) not in (0,'0',None):
        raise RuntimeError(str(x.get('msg',x.get('code'))))
    return x.get('data',x) if isinstance(x,dict) else x

@st.cache_data(ttl=3600,show_spinner=False)
def symbols():
    data=get_json(BASE+'/open/v1/common/symbols')
    items=data.get('list',[]) if isinstance(data,dict) else data
    return [x for x in items if x.get('quoteAsset','').upper()=='TRY' and x.get('spotTradingEnable',1) in (1,'1',True)]

def candles(item,interval):
    typ=int(item.get('type',1))
    raw=item['symbol']
    sym=raw.replace('_','') if typ==1 else raw
    endpoint=API1 if typ==1 else API3 if typ==3 else None
    if not endpoint: raise ValueError('Bu sembol tipi için mum verisi adresi doğrulanmadı')
    data=get_json(endpoint,{'symbol':sym,'interval':interval,'limit':160})
    if not isinstance(data,list) or len(data)<105: raise ValueError('Yetersiz mum verisi')
    df=pd.DataFrame(data)
    for i in [1,2,3,4,5,7]: df[i]=pd.to_numeric(df[i],errors='coerce')
    # Last bar may be incomplete; never use it in scoring.
    df=df.iloc[:-1].copy()
    df.columns=[str(c) for c in df.columns]
    return df

def calc(df,interval):
    c=df['4'];v=df['7'] if '7' in df else df['5']*c
    e7=c.ewm(span=7,adjust=False).mean();e25=c.ewm(span=25,adjust=False).mean();e99=c.ewm(span=99,adjust=False).mean()
    dif=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean()
    dea=dif.ewm(span=9,adjust=False).mean(); hist=dif-dea
    delta=c.diff();up=delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean();dn=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    rsi=100-100/(1+up/dn.replace(0,np.nan))
    ma20=c.rolling(20).mean();std20=c.rolling(20).std()
    width=(4*std20/ma20).iloc[-1]; priorwidth=(4*std20/ma20).iloc[-21:-1].median()
    price=float(c.iloc[-1]);bars=96 if interval=='15m' else 24
    chg=(price/float(c.iloc[-bars-1])-1)*100 if len(c)>bars else np.nan
    vr=float(v.iloc[-1]/v.iloc[-21:-1].mean()) if v.iloc[-21:-1].mean()>0 else 0
    score=0
    score+=25 if 1.4<=vr<=4 else (12 if vr>=1.1 else 0)
    score+=20 if hist.iloc[-1]>0 and hist.iloc[-1]>hist.iloc[-2] else (10 if hist.iloc[-1]>hist.iloc[-2] else 0)
    score+=20 if price>e7.iloc[-1]>e25.iloc[-1] else (10 if price>e25.iloc[-1] else 0)
    score+=15 if 45<=rsi.iloc[-1]<=60 and rsi.iloc[-1]>rsi.iloc[-2] else (7 if 40<=rsi.iloc[-1]<=65 else 0)
    score+=10 if width<priorwidth*.85 else (5 if width<priorwidth else 0)
    score+=10 if price>e99.iloc[-1] else (5 if price>e25.iloc[-1] else 0)
    # Avoid chasing already-extended moves; no predictive probability implied.
    if chg>5: score=max(0,score-20)
    if chg< -10: score=max(0,score-10)
    return {'Fiyat (TL)':price,'Puan':int(score),'RSI14':round(float(rsi.iloc[-1]),1),
            'Hacim / 20 mum':round(vr,2),'24s %':round(float(chg),2),
            'EMA7':float(e7.iloc[-1]),'EMA25':float(e25.iloc[-1]),'EMA99':float(e99.iloc[-1]),
            'MACD':round(float(hist.iloc[-1]),6),'Son mum kapanışı (UTC)':pd.to_datetime(int(df['0'].iloc[-1]),unit='ms',utc=True).strftime('%Y-%m-%d %H:%M')}

def analyze(item,interval):
    df=candles(item,interval)
    row=calc(df,interval)
    row['Parite']=item['symbol'].replace('_','/')
    row['Durum']='İncele' if row['Puan']>=75 else ('İzle' if row['Puan']>=55 else 'Zayıf')
    return row

st.title('📡 MURAT HOCA | KRİPTO RADAR')
st.caption('Binance TR • TRY spot pariteleri • Eğitim ve araştırma amaçlı teknik tarayıcı • Otomatik emir YOK')
with st.sidebar:
    st.header('Tarama ayarları')
    interval=st.selectbox('Mum periyodu',['15m','1h'],index=0)
    limit=st.slider('En fazla kaç parite?',5,250,50,5)
    minscore=st.slider('En az puan',0,100,55,5)
    capital=st.number_input('Toplam sermaye (TL)',min_value=1000,value=200000,step=10000)
    risk=st.number_input('İşlem başına risk (TL)',min_value=100,value=1000,step=100)
    st.info('Sadece tamamlanmış mumlar kullanılır. Puan bir yükseliş olasılığı değildir.')
try:
    all_syms=symbols()
    st.success(f'Binance TR kaynaklı {len(all_syms)} aktif TRY spot paritesi listelendi.')
except Exception as e:
    st.error(f'Binance TR parite listesi alınamadı: {e}')
    st.stop()
if st.button('🔎 Piyasayı şimdi tara',type='primary'):
    items=all_syms[:limit]
    rows=[]; errors=[]
    progress=st.progress(0)
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks={pool.submit(analyze,x,interval):x for x in items}
        for i,f in enumerate(as_completed(tasks),1):
            try: rows.append(f.result())
            except Exception as e: errors.append((tasks[f]['symbol'],str(e)))
            progress.progress(i/len(items))
    st.session_state['rows']=rows
    st.session_state['errors']=errors
    st.session_state['scan_time']=pd.Timestamp.now(tz='Europe/Istanbul').strftime('%Y-%m-%d %H:%M:%S')
if 'rows' in st.session_state:
    rows=st.session_state['rows'];errors=st.session_state['errors']
    st.write(f"**Tarama zamanı:** {st.session_state['scan_time']} (Türkiye) · Başarılı: {len(rows)} · Hata: {len(errors)}")
    if not rows:
        st.error('Hiçbir parite doğrulanamadı. Hataları kontrol edin; sahte veri gösterilmez.')
    else:
        result=pd.DataFrame(rows).sort_values('Puan',ascending=False)
        filtered=result[result['Puan']>=minscore]
        st.subheader('🏆 İlk 5 aday')
        st.dataframe(filtered.head(5)[['Parite','Puan','Durum','Fiyat (TL)','24s %','RSI14','Hacim / 20 mum']],hide_index=True,use_container_width=True)
        st.subheader('Tüm sonuçlar')
        st.dataframe(result,hide_index=True,use_container_width=True)
        st.download_button('📥 CSV indir',result.to_csv(index=False).encode('utf-8-sig'),'kripto_radar.csv','text/csv')
        st.subheader('💰 Risk hesaplayıcı')
        entry=st.number_input('Örnek giriş fiyatı',min_value=0.000001,value=10.0,format='%.6f')
        stop=st.number_input('Örnek stop fiyatı',min_value=0.000001,value=9.8,format='%.6f')
        if stop>=entry: st.warning('Spot uzun pozisyon için stop girişten düşük olmalı.')
        else:
            pos=min(capital,risk/(1-stop/entry))
            st.metric('Teorik azami pozisyon',f'{pos:,.0f} TL')
            st.caption('Komisyon, kayma ve stopun çalışmama riski hariç. Otomatik emir gönderilmez.')
    if errors:
        with st.expander(f'⚠️ Veri hataları ({len(errors)})'):
            st.dataframe(pd.DataFrame(errors,columns=['Parite','Hata']),hide_index=True)
else:
    st.info('Tarama düğmesine basınca gerçek API verileri alınır. Henüz sonuç üretilmedi.')
st.caption('V0.1 prototip • API erişimi ve tüm sembol tipleri gerçek barındırma ortamında test edilmelidir. Haber/kilit açılışı filtresi ve Telegram bu sürümde yok.')
