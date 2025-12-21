import KSR as KSR

ACME_DOMAIN = "acme.operador"
HTABLE = "mytable"
HT_CALLS = "callstable"
SEP_LIST = ";"
SEP_COLS = "|"
N = 5
FAIL_CODES = {480, 486, 408} # 486 Busy/ 480 no answer / 408 Time out

def write_value(active, list):
    return f"active={active}{SEP_COLS}list={list}"

# Mandatory function - module initiation
def mod_init():
    KSR.info("===== Redial 2.0: Python mod init\n")
    return kamailio()

class kamailio:
    # Mandatory function - Kamailio class initiation
    def __init__(self):
        KSR.info('===== Redial 2.0: kamailio.__init__\n')
        KSR.info(f"htable module: {dir(KSR.tm)}\n")

    # Mandatory function - Kamailio subprocesses
    def child_init(self, rank):
        KSR.info('===== Redial 2.0: kamailio.child_init(%d)\n' % rank)
        return 0

    # Function called for REQUEST messages received
    def ksr_request_route(self, msg):
        # REGISTER / DEREGISTER
        if msg.Method == "REGISTER":
            return self.handle_register(msg)

        if msg.Method == "MESSAGE":
            return self.handle_message(msg)

        if msg.Method == "INVITE":
            return self.handle_invite(msg)
        
        if msg.Method in ("ACK", "BYE", "CANCEL"):
            KSR.tm.t_relay()
            return 1

        # Tudo o resto ainda não implementado no Sprint 1
        KSR.sl.send_reply(403, "Forbidden method")
        return 1
    
    def handle_register(self, msg):
        from_domain = KSR.pv.get("$fd")  # domínio do From-URI
        from_uri = KSR.pv.get("$fu") or "" # AoR do From
        to_uri = KSR.pv.get("$tu") or "" # AoR do To

        contact_hdr = KSR.hdr.get("Contact") or ""
        expires_hdr = (KSR.hdr.get("Expires") or "").strip()
            
        KSR.info(f"REGISTER From: {from_uri} (domain: {from_domain})\n")
        KSR.info("REGISTER To: " + (to_uri) + " Contact: " + contact_hdr + "\n") # Extrair AoR do pedido REGISTER (From/To)

        # Rejeitar utilizadores fora do domínio ACME / Validar domínio do AoR
        if from_domain != ACME_DOMAIN:
            KSR.info("REGISTER rejected (invalid domain)\n") # Log de tentativa rejeitada
            KSR.sl.send_reply(403, "Forbidden - Invalid Domain") # Rejeitar pedido com resposta SIP adequada (403 Forbidden)
            return 1 # Garante que nenhum estado ou lista é criado
            
        expires = None
        if expires_hdr.isdigit():
            expires = int(expires_hdr)

        is_deregister = (expires == 0) or ("expires=0" in contact_hdr.replace(" ", ""))

        # DE-registar
        if is_deregister:
            KSR.info("DEREGISTER detetado para " + (to_uri) + "\n")
                
            # Detetar se utilizador está registado antes de remover
            KSR.pv.sets("$ru", to_uri)
            if KSR.registrar.lookup("location") != 1:
                KSR.info("DEREGISTER: utilizador não registado\n") 
                KSR.sl.send_reply(404, "Not Found (not registered)") # 404 se não existir registo
                return 1

            # Atualizar estado de registo na BD (Guarda (REGISTER ou deregister) no usrloc/location)
            # Responder SIP 200 OK com Contact e expires
            if KSR.registrar.save("location", 0) < 0:
                KSR.sl.send_reply(500, "Server Error")
                return 1

            KSR.info(f"DEREGISTER HTABLE ANTES: {KSR.htable.sht_get(HTABLE, from_uri)}\n")
            KSR.htable.sht_rm(HTABLE, from_uri)
            KSR.info(f"DEREGISTER HTABLE DEPOIS: {KSR.htable.sht_get(HTABLE, from_uri)}\n")

            KSR.info(f"DEREGISTER succeeded for {from_uri}\n")
            return 1
            
        # REGISTER
        if KSR.registrar.save("location", 0) < 0:
            KSR.sl.send_reply(500, "Server Error")
            return 1

        value = write_value("0", "")
        KSR.info(f"REGISTER HTABLE ANTES: {KSR.htable.sht_get(HTABLE, from_uri)}\n")
            
        KSR.htable.sht_sets(HTABLE, from_uri, value)
            
        KSR.info(f"REGISTER HTABLE DEPOIS: {KSR.htable.sht_get(HTABLE, from_uri)}\n")
            
        KSR.info(f"Register succeded for {from_uri}\n")

        return 1

    def handle_message(self, msg):

        from_domain = KSR.pv.get("$fd") or ""  # domínio do From-URI
        from_uri = KSR.pv.get("$fu") or "" # AoR do From
        ruri = KSR.pv.get("$ru") or "" # AoR destino
        body = (KSR.pv.get("$rb") or "").strip()

        KSR.info(f"MESSAGE From: {from_uri} To: {ruri} Body: '{body}')\n")

        # Validar destino (redial@acme.operador)
        if ruri != f"sip:redial@{ACME_DOMAIN}":
            KSR.info(f"Not Found '{ruri}'\n")
            KSR.sl.send_reply(404, "Not Found")
            return 1

        # Validar dominio
        if from_domain != ACME_DOMAIN:
            KSR.info("MESSAGE rejected (invalid domain)\n") # Log de tentativa rejeitada
            KSR.sl.send_reply(403, "Forbidden - Invalid Domain")
            return 1

        # Validar se está registado
        reg = KSR.htable.sht_get(HTABLE, from_uri)
        if reg is None or reg == "":
            KSR.sl.send_reply(403, "Forbidden - Not registered")
            KSR.info(f"MESSAGE Forbidden - {from_uri} Not registered\n")
            return 1
        
        # Receber SIP MESSAGE para redial@acme.operador
        parts = body.split() # ACTIVATE user1 user2 parts=[ACTIVE, user1, user2]
        command = parts[0].upper() # command=ACTIVE

        if command == "ACTIVATE":
            dests = parts[1:] # dests=[user1, user2]
            if not dests: # dests=[]
                KSR.sl.send_reply(400, "No destinations provided")
                KSR.info("MESSAGE No destinations provided\n")
                return 1
            
            # Acrescentar destinos à lista de remarcação
            new_list = SEP_LIST.join(dests) # dests=[user1, user2] -> new_list=user1;user2
            new_value = write_value("1", new_list)
            
            KSR.info(f"MESSSAGE HTABLE ANTES: {KSR.htable.sht_get(HTABLE, from_uri)}\n")
            
            KSR.htable.sht_sets(HTABLE, from_uri, new_value)
            
            KSR.info(f"MESSAGE HTABEL DEPOIS: {KSR.htable.sht_get(HTABLE, from_uri)}\n")
            
            KSR.info(f"REDIAL ACTIVE for {from_uri}\n")
            # Responder 200 SIP OK
            KSR.sl.send_reply(200, "Redial 2.0 Activated")
            return 1
        
        if command == "DEACTIVATE": # parts=[DEACTIVATE]
            if parts[1:]: # parts=[DEACTIVATE blabla]
                KSR.info(f"Arguments passed in command\n")
                KSR.sl.send_reply(400, "Arguments passed in command")
                return 1
            
            new_value = write_value("0", "")
            KSR.info(f"MESSSAGE HTABLE ANTES: {KSR.htable.sht_get(HTABLE, from_uri)}\n")

            KSR.htable.sht_sets(HTABLE, from_uri, new_value)

            KSR.info(f"DEACTIVATE HTABLE DEPOIS: {KSR.htable.sht_get(HTABLE, from_uri)}\n")

            KSR.sl.send_reply(200, "Redial 2.0 Deactivated")
            return 1

        KSR.info(f"Invalid command\n")
        KSR.sl.send_reply(400, "Invalid Command")
    
    def handle_invite(self, msg):
        
        from_uri = KSR.pv.get("$fu") or "" # AoR do From
        ruri = str(KSR.pv.get("$ru")) or ""
        call_id = KSR.pv.get("$ci") or ""

        KSR.info(f"INVITE from: {from_uri} To: {ruri} Call-ID: {call_id}\n")

        # ver se originador está registado
        reg = KSR.htable.sht_get(HTABLE, from_uri)
        if reg == None or reg == "":
            KSR.info(f"INVITE from: {from_uri} not registered\n")
            KSR.sl.send_reply(403, "Not registered")
            return KSR.tm.t_relay()
        
        parts = reg.split(SEP_COLS) # parts=[active=1, list=user1;user2;user3]
        active = parts[0].split("=")[1] # =[active=1] =[active, 1] parts=[1]
        list = parts[1].split("=")[1].split(SEP_LIST) # list=[user1, user2, user3]

        # Se serviço não ativo -> chamada normal
        if active != "1": 
            KSR.info("INVITE Redial service not activated, normal call\n")
            return KSR.tm.t_relay()
        
        # Se serviço ativo, mas destino não está na lista -> chamada normal
        if ruri.split("sip:")[1] not in list:
            KSR.info(f"INVITE Redial service active and destination not in redial list, normal call {ruri}\n")
            return KSR.tm.t_relay()
        
        # Serviço ativo e está na lista
        if KSR.tm.t_newtran() < 0:
            KSR.sl.send_reply(500, "Server Error")
            return 1
            
        KSR.info("INVITE Redial service active and destination in redial list, redial control\n")

        KSR.htable.sht_sets(HT_CALLS, call_id + ":armed", "1") # Define se a chamada está sob controlo redial
        KSR.htable.sht_sets(HT_CALLS, call_id + ":tries", "1") # Nº de tentativas
        KSR.htable.sht_sets(HT_CALLS, call_id + ":retry", "0") # Define se é para tentar outra vez
        KSR.htable.sht_sets(HT_CALLS, call_id + ":last_code", "0")
        KSR.htable.sht_sets(HT_CALLS, call_id + ":ruri", ruri)

        KSR.tm.t_on_failure("ksr_failure_route_RDL_FAIL") # Se a transação acabar em falha, chama a ksr_failure_route

        KSR.info(f"INVITE Redial control, tries=1 of {N}\n")

        return KSR.tm.t_relay()
    
    def ksr_reply_route(self, msg):
        
        code = KSR.pv.get("$rs") or "0"
        call_id = KSR.pv.get("$ci") or ""

        armed = KSR.htable.sht_get(HT_CALLS, call_id + ":armed") or "0"
        if armed != "1":
            return 1

        KSR.info(f"INVITE Call-ID={call_id} Code={code}\n")

        if int(code) == 200:
            self._clear_call_state(call_id)
            return 1
        
        if int(code) < 300:
            return 1
        
        KSR.htable.sht_sets(HT_CALLS, call_id + ":last_code", str(code))
        
        if int(code) in FAIL_CODES:
            KSR.htable.sht_sets(HT_CALLS, call_id + ":retry", "1")
        else:
            KSR.htable.sht_sets(HT_CALLS, call_id + ":retry", "0")
            self._clear_call_state(call_id)
        
        return 1
    
    def ksr_failure_route_RDL_FAIL(self, msg):
        call_id = KSR.pv.get("$ci") or ""

        armed = KSR.htable.sht_get(HT_CALLS, call_id + ":armed") or "0"
        if armed != "1":
            return 1
        
        code = KSR.htable.sht_get(HT_CALLS, call_id + ":last_code") or "0"
        retry = KSR.htable.sht_get(HT_CALLS, call_id + ":retry") or "0"
        tries = KSR.htable.sht_get(HT_CALLS, call_id + ":tries") or "1"
        
        KSR.info(f"INVITE Call-ID={call_id} code={code} retry={retry} tries={tries}/{N}\n")

        # Não voltar a tentar a chamada (termina)
        if retry != "1":
            KSR.info("INVITE No retry (decision from reply_route)\n")
            self._clear_call_state(call_id)
            return 1

        # Se chegou ao nº máximo de tentativas termina
        if int(tries) >= N:
            KSR.info("INVITE Reached max tries, stop\n")
            self._clear_call_state(call_id)
            return 1

        # Se ainda não chegou, voltar a tentar
        tries = int(tries) + 1
        tries = str(tries)
        
        KSR.htable.sht_sets(HT_CALLS, call_id + ":tries", tries)
        KSR.htable.sht_sets(HT_CALLS, call_id + ":retry", "0")

        ruri = KSR.htable.sht_get(HT_CALLS, call_id + ":ruri") or ""
        if ruri:
            KSR.pv.sets("$ru", ruri)

        KSR.info(f"INVITE REDIAL attempt {tries}/{N}\n")

        KSR.tm.t_on_failure("ksr_failure_route_RDL_FAIL")

        return KSR.tm.t_relay()

    def _clear_call_state(self, call_id: str):
        KSR.htable.sht_rm(HT_CALLS, call_id + ":armed")
        KSR.htable.sht_rm(HT_CALLS, call_id + ":tries")
        KSR.htable.sht_rm(HT_CALLS, call_id + ":retry")
        KSR.htable.sht_rm(HT_CALLS, call_id + ":last_code")
        KSR.htable.sht_rm(HT_CALLS, call_id + ":ruri")
        KSR.info(f"INVITE Cleared state for {call_id}\n")
        
        return 1
        
    # Function called for messages sent/transit
    def ksr_onsend_route(self, msg):
        KSR.info("===== Redial 2.0: onsend_route: %s\n" % (msg.Type))
        return 1