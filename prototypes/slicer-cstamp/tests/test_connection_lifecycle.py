"""Self-check of actual server methods with reentrant fake Qt signals."""
import ast
from pathlib import Path

tree=ast.parse((Path(__file__).parents[1]/'CStampModule.py').read_text(encoding='utf-8'))
definition=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='_CommandServer')
scope={'CommandDispatcher':object}
exec(compile(ast.Module(body=[definition],type_ignores=[]),'server_methods','exec'),scope)
Server=scope['_CommandServer']

class Signal:
    def connect(self,call): self.call=call
class Socket:
    def __init__(self): self.readyRead=Signal(); self.disconnected=Signal(); self.deleted=0
    def disconnectFromHost(self): self.disconnected.call()
    def deleteLater(self): self.deleted+=1
class Dispatcher:
    def __init__(self): self.drops=0; self.input_owner="hand"
    def on_disconnect(self): self.drops+=1

def test_reentrant_replacement_and_delayed_old_drop_keep_new_connection():
    s=Server.__new__(Server); s._dispatcher=Dispatcher()
    old,new=Socket(),Socket(); old.disconnected.connect(lambda:s._drop(old))
    s._sockets=[old]
    s._server=type('Listener',(),{'nextPendingConnection':lambda self:new})()
    s._on_connection()
    assert s._sockets==[new] and s._dispatcher.drops==1
    s._drop(old); s._drop(old)
    assert s._dispatcher.drops==1
    s._drop(new); s._drop(new)
    assert s._sockets==[] and s._dispatcher.drops==2

def test_close_is_not_mutated_by_synchronous_disconnected_callback():
    s=Server.__new__(Server); s._dispatcher=Dispatcher()
    a,b=Socket(),Socket()
    a.disconnected.connect(lambda:s._drop(a)); b.disconnected.connect(lambda:s._drop(b))
    s._sockets=[a,b]
    s._server=type('Listener',(),{'close':lambda self:None})()
    s.close()
    assert not s._sockets and s._dispatcher.drops==1
    assert a.deleted==b.deleted==1


def test_hand_socket_loss_does_not_disarm_explicit_mouse_owner():
    s=Server.__new__(Server);s._dispatcher=Dispatcher();s._dispatcher.input_owner='mouse'
    socket=Socket();s._sockets=[socket]
    s._drop(socket)
    assert s._dispatcher.drops==0 and not s._sockets
