"""Offline bounded WAV synthesis using explicitly provisioned local weights."""
import argparse,hashlib,json,wave,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from kcee.voice import DEFAULT_VOICE,DEFAULT_SPEED,DEFAULT_LANGUAGE
import numpy as np
from kokoro_onnx import Kokoro
parser=argparse.ArgumentParser();parser.add_argument('--request',required=True);parser.add_argument('--models',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
request=json.loads(Path(args.request).read_text());models=Path(args.models);manifest=json.loads((models/'runtime-manifest.json').read_text())
text=request['text']
if not isinstance(text,str) or not 1<=len(text)<=600:raise ValueError('Voice text exceeds summary limit')
if set(manifest['files'])!={'kokoro-v1.0.int8.onnx','voices-v1.0.bin'}:raise ValueError('Incomplete Kokoro model manifest')
for name,metadata in manifest['files'].items():
    if name not in ('kokoro-v1.0.int8.onnx','voices-v1.0.bin') or hashlib.sha256((models/name).read_bytes()).hexdigest()!=metadata['sha256']:raise ValueError('Kokoro model integrity mismatch')
engine=Kokoro(str(models/'kokoro-v1.0.int8.onnx'),str(models/'voices-v1.0.bin'))
samples,rate=engine.create(text,voice=DEFAULT_VOICE,speed=DEFAULT_SPEED,lang=DEFAULT_LANGUAGE)
if rate!=24000 or not 0<len(samples)<=24000*120 or not np.isfinite(samples).all():raise ValueError('Invalid or oversized synthesized audio')
with wave.open(args.output,'wb') as audio:
    audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(rate);audio.writeframes((np.clip(samples,-1,1)*32767).astype('<i2').tobytes())
