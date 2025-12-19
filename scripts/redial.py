import KSR as KSR

ACME_DOMAIN = "acme.operador"
HTABLE = "mytable"
SEP_LIST = ";"
SEP_COLS = "|"

def write_value(active, list):
    return f"active={active}{SEP_COLS}list={list}"

# Mandatory function - module initiation
def mod_init():
    KSR.info("===== Redial 2.0 Sprint 1: Python mod init\n")
    return kamailio()

class kamailio:
    # Mandatory function - Kamailio class initiation
    def __init__(self):
        KSR.info('===== Redial 2.0 Sprint 1: kamailio.__init__\n')
        KSR.info(f"htable module: {dir(KSR.htable)}\n")


    # Mandatory function - Kamailio subprocesses
    def child_init(self, rank):
        KSR.info('===== Redial 2.0 Sprint 1: kamailio.child_init(%d)\n' % rank)
        return 0

    # Function called for REQUEST messages received
    def ksr_request_route(self, msg):

        # REGISTER / DEREGISTER
        if msg.Method == "REGISTER":

            from_domain = KSR.pv.get("$fd")  # domínio do From-URI
            from_uri = KSR.pv.get("$fu") or "" # AoR do From
            to_uri = KSR.pv.get("$tu") or "" # AoR do To

            contact_hdr = KSR.hdr.get("Contact") or ""
            expires_hdr = (KSR.hdr.get("Expires") or "").strip()
            
            KSR.info(f"REGISTER From: {from_uri} (domain: {from_domain})\n")
            KSR.info("REGISTER To: " + (to_uri) +
                     " Contact: " + contact_hdr + "\n") # Extrair AoR do pedido REGISTER (From/To)

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

        if msg.Method == "MESSAGE":
            return self.handle_message(msg)
        
        # Tudo o resto ainda não implementado no Sprint 1
        KSR.sl.send_reply(403, "Forbidden method for Sprint 1")
        return 1
    
    def handle_message(self, msg):

        from_domain = KSR.pv.get("$fd")  # domínio do From-URI
        from_uri = KSR.pv.get("$fu") or "" # AoR do From
        ruri = KSR.pv.get("$ru") or ""
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
            KSR.info("MESSAGE Forbidden - Not registered\n")
            KSR.sl.send_reply(403, "Forbidden - Not registered")
            return 1
        
        # Receber SIP MESSAGE para redial@acme.operador
        parts = body.split()
        command = parts[0].upper()

        if command == "ACTIVATE":
            dests = parts[1:]
            if not dests:
                KSR.sl.send_reply(400, "No destinations provided")
                return 1
            
            # Validar formato AoRs; Remover destinos duplicados; Acrescentar novos destinos à lista de remarcação
            new_list = SEP_LIST.join(dests)
            new_value = write_value("1", new_list)
            
            KSR.info(f"MESSSAGE HTABLE ANTES: {KSR.htable.sht_get(HTABLE, from_uri)}\n")
            
            KSR.htable.sht_sets(HTABLE, from_uri, new_value)
            
            KSR.info(f"MESSAGE HTABEL DEPOIS: {KSR.htable.sht_get(HTABLE, from_uri)}\n")
            
            #seen = set()
            #for d in dests:
            #    if d.strip().startswith("sip:") and d not in seen:
            #        seen.add(d)
            #        list.append(d)
            
            #if not list:
            #    KSR.sl.send_reply(400, "No valid destination")
            #    return 1

            KSR.info(f"REDIAL ACTIVE for {from_uri}\n")
            # Responder 200 SIP OK
            KSR.sl.send_reply(200, "Redial 2.0 Activated")
            return 1
        
        if command == "DEACTIVATE":
            new_value = write_value("0", "")
            KSR.htable.sht_sets(HTABLE, from_uri, new_value)

            KSR.info(f"DEACTIVATE HTABLE DEPOIS: {KSR.htable.sht_get(HTABLE, from_uri)}\n")

            KSR.sl.send_reply(200, "Redial 2.0 Deactivated")
            return 1

        KSR.info(f"Invalid command\n")
        KSR.sl.send_reply(400, "Invalid Command")



    # Function called for REPLY messages received
    def ksr_reply_route(self, msg):
        KSR.info("===== Redial 2.0 Sprint 1: reply_route - Status: " +
                 str(KSR.pv.get("$rs")) + "\n")
        return 1

    # Function called for messages sent/transit
    def ksr_onsend_route(self, msg):
        KSR.info("===== Redial 2.0 Sprint 1: onsend_route: %s\n" % (msg.Type))
        return 1
    

