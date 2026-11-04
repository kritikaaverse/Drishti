"""Send a supplied JPEG file as an Android-protocol smoke test. Never captures a webcam."""
import argparse
import asyncio
import json
from pathlib import Path
import websockets
async def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',required=True,help='ws://LAPTOP_LAN_IP:8000/api/ws/vision (use wss for TLS)')
    parser.add_argument('--key',required=True)
    parser.add_argument('--image',type=Path,required=True)
    parser.add_argument('--language',choices=['en','hi','mr'],default='en')
    args=parser.parse_args()
    async with websockets.connect(args.url,max_size=4*1024*1024) as socket:
        await socket.send(json.dumps({'role':'camera','api_key':args.key,'device_id':'protocol-test','language':args.language}))
        print(await socket.recv())
        print(await socket.recv())
        await socket.send(args.image.read_bytes())
        print(await socket.recv())
if __name__=='__main__': asyncio.run(main())
