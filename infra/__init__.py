"""Optional, deletable infrastructure glue (not part of the Django app).

Code here is deployed outside the request path (e.g. AWS Lambda). The API stays a
pure OAuth2 resource server; identity lifecycle lives in the IdP.
"""
