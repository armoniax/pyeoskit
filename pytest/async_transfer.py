import asyncio
from pyeoskit import wallet
from pyeoskit.chainapi import ChainApiAsync

#import your account private key here
#wallet.import_key('mywallet', '')

async def test():
    wallet.import_key('mywallet', '5J5UTtxC8R363aegpPvk5CQm1jNNfsKFhACC6uZYGvfaighkABQ')
    eosapi = ChainApiAsync('http://127.0.0.1:8888')
    info = await eosapi.get_info()
    print(info)
    args = {
        'from': 'amax',
        'to': 'produceraaaa',
        'quantity': '1.00000000 AMAX',
        'memo': 'hello,world'
    }
    r = await eosapi.push_action('amax.token', 'transfer', args, {'amax':'active'})
    print(r)

asyncio.run(test())