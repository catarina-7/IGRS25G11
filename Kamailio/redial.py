import ksr

def ksr_request_route():
    ksr.info("RECEBI UMA MENSAGEM SIP!\n")
    return 1

def ksr_onreply_route():
    ksr.info("DETECTEI UMA RESPOSTA SIP!\n")
    return 1