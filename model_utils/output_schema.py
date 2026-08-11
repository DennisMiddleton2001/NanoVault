class OutputSchema():
    def __init__(self):
        pass

    def request(self, pipeline, command, params):
        self.request = {
            "pipeline" : pipeline,
            "command"  : command,
            "params"    : params
            }
    
    def response(self, http_status, error, message, return_values):
        reply = {
            "status" : http_status,
            "error"  : error,
            "message": message,
            "results": len(return_values),
            "return_values"  : return_values
        }

        response_payload = dict()
        response_payload["request"] = self.request
        response_payload["reply"] = self.reply
        return response_payload