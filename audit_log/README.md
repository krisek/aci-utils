# audit_log

The audit_log_dog library connects over websocket to the given fabric, maintains the subscribtion to to the audit log and dumps the received events into a log file. Two example impementations are included, the audit_log.py script connects to one fabric while the audit_log_mt.py script can download audit logs from several fabrics in a multithreaded fashion. 

The library maintains the WS subscription and it handles (until a certain extent) ACI disconnects too. This doesn't mean that it is 100% certain that no audit logs get lost.

It makes use of the lomond WS library as the others seemed to be unreliable.

NOTE: the login.json file required for authentication is a simple JSON that can be posted to the ACI in the authentication request:

```json
{
  "aaaUser" : {
    "attributes" : {
      "name" : "__user__",
      "pwd" : "__pass__"
    }
  }
}
```
