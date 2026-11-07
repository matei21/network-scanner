FINDING_TEMPLATES = {
    "TELNET_OPEN": {
        "severity": "high",
        "points": 20,
        "explanation": {
            "ro": (
                "Acest dispozitiv permite conectarea la distanta prin Telnet, "
                "un protocol care trimite totul necriptat, inclusiv parola. "
                "Oricine din reteaua ta poate vedea ce tastezi."
            ),
            "en": (
                "This device allows remote login via Telnet, a protocol that "
                "sends everything unencrypted, including your password. "
                "Anyone on your network can see what you type."
            ),
        },
        "metaphor": {
            "ro": "Ca si cum ai vorbi parola cu voce tare intr-o camera plina de straini.",
            "en": "Like saying your password out loud in a room full of strangers.",
        },
        "fix_steps": {
            "ro": [
                "Deschide setarile routerului in browser (scrie adresa IP in bara de adrese)",
                "Cauta sectiunea 'Administration' sau 'Management'",
                "Gaseste optiunea 'Telnet' si dezactiveaz-o",
                "Salveaza setarile si reporneste routerul",
            ],
            "en": [
                "Open your router settings in a browser (type the IP address in the address bar)",
                "Look for the 'Administration' or 'Management' section",
                "Find the 'Telnet' option and disable it",
                "Save settings and restart the router",
            ],
        },
        "cis_control": "CIS Control 3.10 - Encrypt Sensitive Data in Transit",
        "owasp_iot": "OWASP IoT T1 - Weak, Guessable, or Hardcoded Passwords",
    },
    "RDP_EXPOSED": {
        "severity": "high",
        "points": 20,
        "explanation": {
            "ro": (
                "Desktop-ul acestui calculator poate fi accesat de la distanta prin RDP. "
                "Daca nu e protejat cu o parola puternica, oricine din retea poate prelua controlul."
            ),
            "en": (
                "This computer's desktop can be accessed remotely via RDP. "
                "Without a strong password, anyone on the network could take control."
            ),
        },
        "metaphor": {
            "ro": "Ca si cum ai lasa calculatorul deschis si oricine s-ar putea aseza la el.",
            "en": "Like leaving your computer unlocked for anyone to sit down and use.",
        },
        "fix_steps": {
            "ro": [
                "Deschide Settings (Setari) pe calculator",
                "Cauta 'Remote Desktop' sau 'Desktop la distanta'",
                "Dezactiveaza optiunea daca nu o folosesti",
                "Daca ai nevoie de ea, seteaza o parola puternica si activeaza Network Level Authentication",
            ],
            "en": [
                "Open Settings on the computer",
                "Search for 'Remote Desktop'",
                "Disable it if you don't use it",
                "If you need it, set a strong password and enable Network Level Authentication",
            ],
        },
        "cis_control": "CIS Control 4.1 - Establish and Maintain a Secure Configuration Process",
        "owasp_iot": "OWASP IoT T1 - Weak, Guessable, or Hardcoded Passwords",
    },
    "VNC_EXPOSED": {
        "severity": "high",
        "points": 20,
        "explanation": {
            "ro": (
                "Ecranul acestui dispozitiv poate fi vazut si controlat de la distanta prin VNC. "
                "Fara o parola puternica, oricine din retea poate vedea ce faceti pe ecran."
            ),
            "en": (
                "This device's screen can be viewed and controlled remotely via VNC. "
                "Without a strong password, anyone on the network can see your screen."
            ),
        },
        "metaphor": {
            "ro": "Ca si cum cineva s-ar uita peste umarul tau la tot ce faci pe ecran.",
            "en": "Like someone looking over your shoulder at everything on your screen.",
        },
        "fix_steps": {
            "ro": [
                "Deschide aplicatia VNC Server de pe acest dispozitiv",
                "Daca nu folosesti VNC, dezinstaleaz-o sau opreste serviciul",
                "Daca ai nevoie de VNC, seteaza o parola puternica in setarile aplicatiei",
                "Restrictioneaza accesul doar la adresele IP de care ai nevoie",
            ],
            "en": [
                "Open the VNC Server application on this device",
                "If you don't use VNC, uninstall it or stop the service",
                "If you need VNC, set a strong password in the application settings",
                "Restrict access to only the IP addresses you need",
            ],
        },
        "cis_control": "CIS Control 4.1 - Establish and Maintain a Secure Configuration Process",
        "owasp_iot": "OWASP IoT T3 - Insecure Ecosystem Interfaces",
    },
    "DB_EXPOSED": {
        "severity": "high",
        "points": 20,
        "explanation": {
            "ro": (
                "O baza de date este accesibila din retea. "
                "Daca nu e protejata cu parola, oricine ar putea citi sau sterge datele stocate."
            ),
            "en": (
                "A database is accessible from the network. "
                "Without password protection, anyone could read or delete the stored data."
            ),
        },
        "metaphor": {
            "ro": "Ca si cum ai lasa un sertar cu documente importante deschis, fara lacet.",
            "en": "Like leaving a drawer with important documents unlocked and open.",
        },
        "fix_steps": {
            "ro": [
                "Configureaza baza de date sa accepte conexiuni doar de la adresa 127.0.0.1 (doar local)",
                "Seteaza o parola puternica pentru accesul la baza de date",
                "Daca nu stii de ce e aceasta baza de date, opreste serviciul",
                "Verifica cu un specialist IT daca datele stocate sunt sensibile",
            ],
            "en": [
                "Configure the database to only accept connections from 127.0.0.1 (localhost only)",
                "Set a strong password for database access",
                "If you don't know why this database is running, stop the service",
                "Check with an IT specialist if the stored data is sensitive",
            ],
        },
        "cis_control": "CIS Control 3.10 - Encrypt Sensitive Data in Transit",
        "owasp_iot": "OWASP IoT T3 - Insecure Ecosystem Interfaces",
    },
    "CAMERA_STREAM_EXPOSED": {
        "severity": "high",
        "points": 20,
        "explanation": {
            "ro": (
                "Camera video transmite imagini accesibile oricui din retea. "
                "Oricine conectat la reteaua ta WiFi poate vedea ce filmeaza camera."
            ),
            "en": (
                "The video camera is streaming footage accessible to anyone on the network. "
                "Anyone connected to your WiFi can see what the camera is recording."
            ),
        },
        "metaphor": {
            "ro": "Ca si cum ai avea o camera de supraveghere care transmite live pentru toti vecinii.",
            "en": "Like having a security camera that broadcasts live to all your neighbors.",
        },
        "fix_steps": {
            "ro": [
                "Deschide setarile camerei in browser (scrie adresa IP a camerei)",
                "Cauta sectiunea 'Network' sau 'RTSP Settings'",
                "Activeaza 'Authentication Required' sau 'Require Password'",
                "Seteaza o parola puternica pentru accesul la camera",
                "Verifica ca streamul nu e vizibil fara parola",
            ],
            "en": [
                "Open camera settings in a browser (type the camera's IP address)",
                "Look for 'Network' or 'RTSP Settings' section",
                "Enable 'Authentication Required' or 'Require Password'",
                "Set a strong password for camera access",
                "Verify the stream is not visible without a password",
            ],
        },
        "cis_control": "CIS Control 3.10 - Encrypt Sensitive Data in Transit",
        "owasp_iot": "OWASP IoT T6 - Insufficient Privacy Protection",
    },
    "OUTDATED_SERVICE": {
        "severity": "high",
        "points": 20,
        "explanation": {
            "ro": (
                "Acest software are o versiune veche cu probleme de securitate cunoscute. "
                "Atacatorii stiu exact cum sa exploateze aceste probleme."
            ),
            "en": (
                "This software is running an old version with known security issues. "
                "Attackers know exactly how to exploit these vulnerabilities."
            ),
        },
        "metaphor": {
            "ro": "Ca si cum ai avea o incuietoare sparta pe care hotii stiu cum sa o deschida.",
            "en": "Like having a broken lock that burglars know how to pick.",
        },
        "fix_steps": {
            "ro": [
                "Identifica programul si versiunea curenta (vezi detaliile de mai sus)",
                "Cauta pe site-ul producatorului ultima versiune disponibila",
                "Actualizeaza la cea mai noua versiune",
                "Daca actualizarea nu e posibila, inlocuieste cu o alternativa moderna",
                "Dupa actualizare, scaneaza din nou reteaua sa verifici",
            ],
            "en": [
                "Identify the software and its current version (see details above)",
                "Check the manufacturer's website for the latest available version",
                "Update to the newest version",
                "If updating is not possible, replace with a modern alternative",
                "After updating, scan the network again to verify",
            ],
        },
        "cis_control": "CIS Control 2.2 - Ensure Authorized Software is Currently Supported",
        "owasp_iot": "OWASP IoT T4 - Lack of Secure Update Mechanism",
    },
    "FTP_CLEARTEXT": {
        "severity": "medium",
        "points": 10,
        "explanation": {
            "ro": (
                "Acest dispozitiv permite transferul de fisiere prin FTP, un protocol fara criptare. "
                "Fisierele si parolele sunt trimise in clar si pot fi interceptate."
            ),
            "en": (
                "This device allows file transfers via FTP, an unencrypted protocol. "
                "Files and passwords are sent in plain text and can be intercepted."
            ),
        },
        "metaphor": {
            "ro": "Ca si cum ai trimite scrisori importante fara plic -- oricine le poate citi pe drum.",
            "en": "Like sending important letters without an envelope -- anyone can read them along the way.",
        },
        "fix_steps": {
            "ro": [
                "Inlocuieste FTP cu SFTP (versiunea sigura, criptata)",
                "Daca nu poti folosi SFTP, dezactiveaza FTP daca nu il folosesti",
                "Daca ai nevoie de FTP, limiteaza accesul doar la dispozitivele de incredere",
            ],
            "en": [
                "Replace FTP with SFTP (the secure, encrypted version)",
                "If you can't use SFTP, disable FTP if you don't use it",
                "If you need FTP, restrict access to trusted devices only",
            ],
        },
        "cis_control": "CIS Control 3.10 - Encrypt Sensitive Data in Transit",
        "owasp_iot": "OWASP IoT T3 - Insecure Ecosystem Interfaces",
    },
    "HTTP_ADMIN_CLEARTEXT": {
        "severity": "medium",
        "points": 10,
        "explanation": {
            "ro": (
                "Pagina de administrare a acestui dispozitiv nu foloseste criptare. "
                "Cand te autentifici, parola ta poate fi vazuta de oricine din retea."
            ),
            "en": (
                "This device's admin page does not use encryption. "
                "When you log in, your password can be seen by anyone on the network."
            ),
        },
        "metaphor": {
            "ro": "Ca si cum ai scrie parola pe o foaie si ai arata-o tuturor din camera.",
            "en": "Like writing your password on a sheet of paper and showing it to everyone in the room.",
        },
        "fix_steps": {
            "ro": [
                "Deschide setarile dispozitivului in browser",
                "Cauta optiunea de HTTPS sau SSL in setarile de administrare",
                "Activeaza HTTPS si dezactiveaza accesul prin HTTP simplu",
                "Dupa activare, acceseaza pagina prin https:// in loc de http://",
            ],
            "en": [
                "Open the device settings in a browser",
                "Look for HTTPS or SSL option in admin settings",
                "Enable HTTPS and disable plain HTTP access",
                "After enabling, access the page via https:// instead of http://",
            ],
        },
        "cis_control": "CIS Control 3.10 - Encrypt Sensitive Data in Transit",
        "owasp_iot": "OWASP IoT T3 - Insecure Ecosystem Interfaces",
    },
    "SMB_EXPOSED": {
        "severity": "medium",
        "points": 10,
        "explanation": {
            "ro": (
                "Partajarea de fisiere Windows (SMB) este activata pe acest dispozitiv. "
                "Oricine din retea ar putea incerca sa acceseze fisierele partajate."
            ),
            "en": (
                "Windows file sharing (SMB) is enabled on this device. "
                "Anyone on the network could try to access the shared files."
            ),
        },
        "metaphor": {
            "ro": "Ca si cum ai lasa un dosar cu fisierele tale pe o masa la care poate sta oricine.",
            "en": "Like leaving a folder with your files on a table where anyone can sit.",
        },
        "fix_steps": {
            "ro": [
                "Deschide Settings (Setari) → Network & Internet → Advanced sharing settings",
                "Dezactiveaza 'File and Printer Sharing' daca nu ai nevoie",
                "Daca ai nevoie de partajare, seteaza parola si limiteaza accesul",
                "Verifica ce foldere sunt partajate si sterge partajarile inutile",
            ],
            "en": [
                "Open Settings → Network & Internet → Advanced sharing settings",
                "Disable 'File and Printer Sharing' if you don't need it",
                "If you need sharing, set a password and restrict access",
                "Check which folders are shared and remove unnecessary shares",
            ],
        },
        "cis_control": "CIS Control 3.3 - Configure Data Access Control Lists",
        "owasp_iot": "OWASP IoT T3 - Insecure Ecosystem Interfaces",
    },
    "MQTT_EXPOSED": {
        "severity": "medium",
        "points": 10,
        "explanation": {
            "ro": (
                "Un broker MQTT (folosit de dispozitive smart home) este accesibil din retea. "
                "Fara autentificare, oricine poate trimite comenzi dispozitivelor tale inteligente."
            ),
            "en": (
                "An MQTT broker (used by smart home devices) is accessible on the network. "
                "Without authentication, anyone can send commands to your smart devices."
            ),
        },
        "metaphor": {
            "ro": "Ca si cum oricine ar putea apasa butoanele din casa ta inteligenta.",
            "en": "Like anyone being able to press the buttons in your smart home.",
        },
        "fix_steps": {
            "ro": [
                "Deschide setarile broker-ului MQTT (de obicei prin interfata web a hub-ului smart home)",
                "Activeaza autentificarea (username si parola)",
                "Seteaza o parola puternica",
                "Daca nu folosesti dispozitive smart home, opreste serviciul MQTT",
            ],
            "en": [
                "Open the MQTT broker settings (usually through the smart home hub's web interface)",
                "Enable authentication (username and password)",
                "Set a strong password",
                "If you don't use smart home devices, stop the MQTT service",
            ],
        },
        "cis_control": "CIS Control 4.1 - Establish and Maintain a Secure Configuration Process",
        "owasp_iot": "OWASP IoT T1 - Weak, Guessable, or Hardcoded Passwords",
    },
    "UPNP_EXPOSED": {
        "severity": "medium",
        "points": 10,
        "explanation": {
            "ro": (
                "UPnP este activ, ceea ce permite oricarui dispozitiv din retea sa deschida "
                "porturi pe router automat, fara sa te intrebe."
            ),
            "en": (
                "UPnP is active, which allows any device on the network to automatically "
                "open ports on your router without asking you."
            ),
        },
        "metaphor": {
            "ro": "Ca si cum oricine din casa ar putea deschide usa de la intrare fara sa te intrebe.",
            "en": "Like anyone in the house being able to open the front door without asking you.",
        },
        "fix_steps": {
            "ro": [
                "Deschide setarile routerului in browser",
                "Cauta sectiunea 'UPnP' (de obicei in Advanced sau NAT)",
                "Dezactiveaza UPnP",
                "Daca un dispozitiv nu mai functioneaza, configureaza manual porturile necesare",
            ],
            "en": [
                "Open your router settings in a browser",
                "Look for the 'UPnP' section (usually in Advanced or NAT)",
                "Disable UPnP",
                "If a device stops working, manually configure the required ports",
            ],
        },
        "cis_control": "CIS Control 4.1 - Establish and Maintain a Secure Configuration Process",
        "owasp_iot": "OWASP IoT T3 - Insecure Ecosystem Interfaces",
    },
    "SNMP_EXPOSED": {
        "severity": "medium",
        "points": 10,
        "explanation": {
            "ro": (
                "Protocolul de management SNMP este accesibil. "
                "Poate fi folosit pentru a citi informatii detaliate despre dispozitiv sau chiar pentru a-i schimba setarile."
            ),
            "en": (
                "The SNMP management protocol is accessible. "
                "It can be used to read detailed device information or even change its settings."
            ),
        },
        "metaphor": {
            "ro": "Ca si cum cineva ar putea citi toate specificatiile casei tale si ar putea schimba incuietorile.",
            "en": "Like someone being able to read all your house specs and change the locks.",
        },
        "fix_steps": {
            "ro": [
                "Deschide setarile dispozitivului (de obicei routerul)",
                "Cauta sectiunea 'SNMP' in setarile avansate",
                "Dezactiveaza SNMP daca nu il folosesti",
                "Daca ai nevoie de SNMP, schimba community string-ul din 'public' intr-o parola puternica",
            ],
            "en": [
                "Open the device settings (usually the router)",
                "Look for the 'SNMP' section in advanced settings",
                "Disable SNMP if you don't use it",
                "If you need SNMP, change the community string from 'public' to a strong password",
            ],
        },
        "cis_control": "CIS Control 4.1 - Establish and Maintain a Secure Configuration Process",
        "owasp_iot": "OWASP IoT T3 - Insecure Ecosystem Interfaces",
    },
    "PRINTER_RAW_EXPOSED": {
        "severity": "low",
        "points": 5,
        "explanation": {
            "ro": (
                "Imprimanta accepta comenzi de printare de la oricine din retea. "
                "Cineva ar putea trimite documente la imprimanta ta fara permisiunea ta."
            ),
            "en": (
                "The printer accepts print jobs from anyone on the network. "
                "Someone could send documents to your printer without your permission."
            ),
        },
        "metaphor": {
            "ro": "Ca si cum oricine ar putea folosi imprimanta ta fara sa te intrebe.",
            "en": "Like anyone being able to use your printer without asking.",
        },
        "fix_steps": {
            "ro": [
                "Deschide setarile imprimantei (de obicei prin interfata web la adresa IP a imprimantei)",
                "Cauta setarile de securitate sau acces",
                "Activeaza autentificarea sau limiteaza accesul la anumite dispozitive",
            ],
            "en": [
                "Open the printer settings (usually through web interface at the printer's IP address)",
                "Look for security or access settings",
                "Enable authentication or restrict access to specific devices",
            ],
        },
        "cis_control": "CIS Control 4.1 - Establish and Maintain a Secure Configuration Process",
        "owasp_iot": "OWASP IoT T3 - Insecure Ecosystem Interfaces",
    },
    "UNKNOWN_DEVICE": {
        "severity": "low",
        "points": 5,
        "explanation": {
            "ro": (
                "Am gasit un dispozitiv pe care nu il pot identifica -- nu stiu producatorul si nu are nume. "
                "Daca nu il recunosti, s-ar putea sa fie cineva conectat la reteaua ta fara permisiune."
            ),
            "en": (
                "I found a device I can't identify -- unknown manufacturer and no name. "
                "If you don't recognize it, someone may have joined your network without permission."
            ),
        },
        "metaphor": {
            "ro": "Ca si cum ai gasi un strain in casa si nu stii cine e.",
            "en": "Like finding a stranger in your house and not knowing who they are.",
        },
        "fix_steps": {
            "ro": [
                "Verifica toate dispozitivele tale -- telefoane, tablete, laptopuri, smart TV-uri",
                "Daca nu recunosti acest dispozitiv, schimba parola WiFi imediat",
                "Dupa schimbarea parolei, reconecteaza doar dispozitivele tale",
                "Scaneaza din nou reteaua sa verifici ca dispozitivul necunoscut a disparut",
            ],
            "en": [
                "Check all your devices -- phones, tablets, laptops, smart TVs",
                "If you don't recognize this device, change your WiFi password immediately",
                "After changing the password, reconnect only your own devices",
                "Scan the network again to verify the unknown device is gone",
            ],
        },
        "cis_control": "CIS Control 1.1 - Establish and Maintain Detailed Enterprise Asset Inventory",
        "owasp_iot": "OWASP IoT T9 - Insecure Default Settings",
    },
    "SSH_OPEN": {
        "severity": "info",
        "points": 0,
        "explanation": {
            "ro": (
                "Acest dispozitiv permite conectarea la distanta prin SSH, un protocol criptat. "
                "Nu e periculos in sine, dar asigura-te ca folosesti o parola puternica sau chei SSH."
            ),
            "en": (
                "This device allows remote login via SSH, an encrypted protocol. "
                "It's not dangerous by itself, but make sure you use a strong password or SSH keys."
            ),
        },
        "metaphor": {
            "ro": "Ca o usa cu incuietoare buna -- sigura daca ai o cheie puternica.",
            "en": "Like a door with a good lock -- safe if you have a strong key.",
        },
        "fix_steps": {
            "ro": [
                "Verifica ca folosesti o parola puternica sau autentificare cu chei SSH",
                "Dezactiveaza autentificarea cu parola daca folosesti chei SSH",
                "Daca nu ai nevoie de SSH, dezactiveaz-l",
            ],
            "en": [
                "Make sure you use a strong password or SSH key authentication",
                "Disable password authentication if you use SSH keys",
                "If you don't need SSH, disable it",
            ],
        },
        "cis_control": "CIS Control 4.1 - Establish and Maintain a Secure Configuration Process",
        "owasp_iot": "N/A - SSH is encrypted and informational only",
    },
}


def get_template(finding_code, language="ro"):
    """Returneaza template-ul pentru un finding code dat."""
    template = FINDING_TEMPLATES.get(finding_code)
    if not template:
        return None

    return {
        "explanation": template["explanation"].get(language, template["explanation"]["en"]),
        "metaphor": template["metaphor"].get(language, template["metaphor"]["en"]),
        "fix_steps": template["fix_steps"].get(language, template["fix_steps"]["en"]),
        "severity": template["severity"],
        "points": template["points"],
        "cis_control": template["cis_control"],
        "owasp_iot": template["owasp_iot"],
    }


def get_all_finding_codes():
    """Returneaza lista tuturor codurilor de findings disponibile."""
    return list(FINDING_TEMPLATES.keys())
