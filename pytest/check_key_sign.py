import os
from pyeoskit import eosapi, wallet
#import your account private key here
wallet.import_key('mywallet', '5J5UTtxC8R363aegpPvk5CQm1jNNfsKFhACC6uZYGvfaighkABQ')

eosapi.set_node('http://127.0.0.1:8888')
info = eosapi.get_info()
#print(info)
pubkey = eosapi.get_public_key('5J5UTtxC8R363aegpPvk5CQm1jNNfsKFhACC6uZYGvfaighkABQ')
print(pubkey)
pubkeys = wallet.get_public_keys()
print(pubkeys)
digest = 'da99a670bc32a4775bef3d0a27e63631d3b70d099f955aec80fe8ab23a209ed3'
sign = eosapi.sign_digest( digest,'5J5UTtxC8R363aegpPvk5CQm1jNNfsKFhACC6uZYGvfaighkABQ')
re_pubkey = eosapi.recover_key(digest, sign)
assert pubkey == re_pubkey
print(sign)
