
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import sqlite3, io, re, os

DB="retail.db"
app=FastAPI(title="Retail Merchandiser Live API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

ALIASES={
"store":["Location","Store","Location Name","Location Code"],
"brand":["Brand","Sub Brand"],
"category":["Category","Item Category","OFP Class","Class","Item Class"],
"gender":["Gender","Gender Dept","Gender Department"],
"item":["Item","Item Code","Style","Style Code","SKU","Barcode"],
"sales":["TW Sales","Sales Qty","TW Qty","Sales"],
"stock":["Stock Qty","SOH","Stock","Available Qty"],
"mtd":["MTD","MTD Sales","MTD Qty"],
"ytd":["YTD","YTD Sales","YTD Qty"],
"l4w":["L4W Qty","L4W Sales","L4W"],
"age":["Ageing Days","Ageing","Age Days","Days"]}

def pick(df,names):
    low={str(c).strip().lower():c for c in df.columns}
    for n in names:
        if n.lower() in low:return low[n.lower()]
    return None

def clean(df):
    out=pd.DataFrame()
    for k,names in ALIASES.items():
        c=pick(df,names)
        out[k]=df[c] if c else ""
    for k in ["sales","stock","mtd","ytd","l4w","age"]:
        out[k]=pd.to_numeric(out[k].astype(str).str.replace(",","",regex=False),errors="coerce").fillna(0)
    return out

def init():
    con=sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS retail (store TEXT,brand TEXT,category TEXT,gender TEXT,item TEXT,sales REAL,stock REAL,mtd REAL,ytd REAL,l4w REAL,age REAL)")
    con.commit();con.close()
init()

@app.get("/api/health")
def health(): return {"status":"LIVE"}

@app.post("/api/upload")
async def upload(file: UploadFile=File(...)):
    raw=await file.read()
    try:
        if file.filename.lower().endswith(".csv"):
            df=pd.read_csv(io.BytesIO(raw))
        else:
            df=pd.read_excel(io.BytesIO(raw))
        data=clean(df)
        con=sqlite3.connect(DB)
        data.to_sql("retail",con,if_exists="replace",index=False)
        con.close()
        return {"status":"success","rows":len(data),"columns":list(df.columns)}
    except Exception as e:
        raise HTTPException(400,str(e))

@app.get("/api/options")
def options():
    con=sqlite3.connect(DB)
    result={}
    for c in ["store","brand","category","gender"]:
        result[c]=[x[0] for x in con.execute(f"SELECT DISTINCT {c} FROM retail WHERE {c}<>'' ORDER BY {c}").fetchall()]
    con.close(); return result

@app.get("/api/kpi")
def kpi(store="",brand="",category="",gender=""):
    con=sqlite3.connect(DB)
    where=[];p=[]
    for c,v in [("store",store),("brand",brand),("category",category),("gender",gender)]:
        if v: where.append(f"{c}=?");p.append(v)
    w=(" WHERE "+" AND ".join(where)) if where else ""
    q=f"""SELECT COALESCE(SUM(sales),0),COALESCE(SUM(stock),0),COALESCE(SUM(mtd),0),
                 COALESCE(SUM(ytd),0),COUNT(*) FROM retail{w}"""
    sales,stock,mtd,ytd,items=con.execute(q,p).fetchone()
    oos=con.execute(f"SELECT COUNT(*) FROM retail{w}{' AND ' if w else ' WHERE '}stock<=0",p).fetchone()[0]
    l4w=con.execute(f"SELECT COALESCE(SUM(l4w),0) FROM retail{w}",p).fetchone()[0]
    con.close()
    return {"sales":sales,"stock":stock,"woc":stock/(l4w/4) if l4w else 0,"oos":oos,"mtd":mtd,"ytd":ytd,"items":items}

@app.get("/api/actions")
def actions(limit:int=500):
    con=sqlite3.connect(DB)
    q="""SELECT store,brand,item,sales,stock,age,
          CASE WHEN stock<=0 THEN 'OOS' WHEN sales>0 AND stock/(sales/4)<2 THEN 'Low WOC' ELSE 'Healthy' END action,
          MAX(0,CAST(sales AS REAL)-stock) refill
          FROM retail ORDER BY CASE WHEN stock<=0 THEN 0 WHEN sales>0 AND stock/(sales/4)<2 THEN 1 ELSE 2 END, refill DESC LIMIT ?"""
    df=pd.read_sql_query(q,con,params=[limit]);con.close()
    return df.fillna("").to_dict("records")
