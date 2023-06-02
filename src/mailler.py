import imaplib
import email


'''
imap_ssl_host = 'imap.gmail.com'
imap_ssl_port = 993
username = 'your_email@gmail.com'
password = 'your app password'
Generate it in your Google account security
'''

class EmailConnector():
    def __init__(self,username,password,imap_ssl_host='imap.gmail.com',imap_ssl_port=993):
        self.imap_ssl_host = imap_ssl_host
        self.imap_ssl_port = imap_ssl_port
        self.username=username
        self.password=password
        self.verbose = True
        self.imap_ssl_connexion()
               
    def imap_ssl_connexion(self):
        try:
            self.imap_ssl = imaplib.IMAP4_SSL(host="imap.gmail.com", port=imaplib.IMAP4_SSL_PORT)
        except Exception as e:
            print(f"ErrorType : {type(e).__name__}, Error : {e}")
            raise SystemError("Can't create IMAP server") from e
        if self.verbose:
            print(f"Connection Object : {self.imap_ssl}")

    def print_verbose(self,resp_code):
        if self.verbose:
            print(f"Response Code : {resp_code}")

    def connect_mailbox(self):  # sourcery skip: class-extract-method
        try:
            resp_code, response = self.imap_ssl.login(self.username, self.password)
        except Exception as e:
            print(f"ErrorType : {type(e).__name__}, Error : {e}")
            resp_code, response = None, None
            return False
        self.print_verbose(resp_code)
        return True
        
    def logout_mailbox(self):
        try:
            resp_code, response = self.imap_ssl.logout()
        except Exception as e:
            print(f"ErrorType : {type(e).__name__}, Error : {e}")
            resp_code, response = None, None
            return False
        self.print_verbose(resp_code)
        self.print_verbose(response[0].decode())
        return True
    
    def list_mailbox_directory(self, do_print = False):
        try:
            resp_code, directories = self.imap_ssl.list()
        except Exception as e:
            print(f"ErrorType : {type(e).__name__}, Error : {e}")
            resp_code, directories = None, None
            return None
        self.print_verbose(resp_code)
        if do_print:
            print("========= List of Directories =================\n")
            for directory in directories:
                print(directory.decode())
        return directories
    
    def set_directory(self,directory):
        resp_code, mail_count = self.imap_ssl.select(mailbox=directory, readonly=True)
        self.print_verbose(resp_code)
        return int(mail_count[0])
            
    def search_emails(self, field,key_word ):
        '''
        field could be FROM, TO, SUBJECT, CC, BCC
        '''
        resp_code, mails = self.imap_ssl.search(None, field, key_word)
        self.print_verbose(resp_code)
        return [int(x) for x in mails[0].decode().split()]

    def print_message(self,  message):
        print("================== Start of Mail  ====================")
        print(f'From       : {message.get("From")}')
        print(f'To         : {message.get("To")}')
        print(f'Bcc        : {message.get("Bcc")}')
        print(f'Date       : {message.get("Date")}')
        print(f'Subject    : {message.get("Subject")}')
        print("Body : ")
        for part in message.walk():
            if part.get_content_type() == "text/plain": ## Only Printing Text of mail. It can have attachements
                body_lines = part.as_string().split("\n")
                print("\n".join(body_lines[:6])) ### Print first few lines of message
        print(f"================== End of Mail  ====================\n")
         
             
    def get_email(self, mail_id, do_print = False):
        resp_code, mail_data = self.imap_ssl.fetch(str(mail_id), '(RFC822)') ## Fetch mail data.
        message = email.message_from_bytes(mail_data[0][1]) ## Construct Message from mail data     
        if do_print:
            self.print_message(message)
        self.print_verbose(resp_code)
        return email.message_from_string(mail_data[0][1].decode('utf-8'))

