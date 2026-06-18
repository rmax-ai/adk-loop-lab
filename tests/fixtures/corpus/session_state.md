# In-Memory Session State

In-memory session state keeps recent context inside the running process or ADK
session. Reads are fast because there is no disk round-trip, which makes this
approach attractive for short interactive loops. It also fits workflows where
the runtime already carries a session object for tool outputs and intermediate
plans. The limitation is durability: if the worker crashes or the process is
restarted, the session state disappears. Teams usually pair session state with a
durable backing store when correctness across restarts matters.
