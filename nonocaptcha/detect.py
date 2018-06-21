

class Detect(object):
    def __init__(self, log):
        self.detected = False
        self.log = log
    
    async def check_detection(self, frame, timeout, wants_true=""):
        """Checks if "Try again later", "please solve more modal appears 
        or success"""
    
        # I got lazy here
        bot_header = (
            "parent.frames[1].document.getElementsByClassName"
            '("rc-doscaptcha-header-text")[0]'
        )
        try_again_header = (
            "parent.frames[1].document.getElementsByClassName"
            '("rc-audiochallenge-error-message")[0]'
        )
        checkbox = (
            'parent.frames[0].document.getElementById("recaptcha-anchor")'
        )
    
        if wants_true:
            wants_true = f"if({wants_true}) return true;"
    
        # if isinstance(wants_true, list):
        #    l = [f'if({i}) return true;' for i in wants_true]
        #    wants_true = '\n'.join(wants_true)
    
        func ="""() => {
            %s
            
            var elem_bot = %s;
            if(typeof elem_bot !== 'undefined'){
                if(elem_bot.innerText === 'Try again later'){
                    parent.window.wasdetected = true;
                    return true;
                }
            }
    
            var elem_try = %s;
            if(typeof elem_try !== 'undefined'){
                if(elem_try.innerText.indexOf('please solve more.') >= 0){
                    elem_try.parentNode.removeChild(elem_try);
                    return true;
                }
            }
            
            var elem_anchor = %s;
            if(elem_anchor.getAttribute("aria-checked") === "true"){
                return true
            }
        }"""% (
            wants_true,
            bot_header,
            try_again_header,
            checkbox,
        )
        try:
            await frame.waitForFunction(func, timeout=timeout * 1000)
        except:
            raise
        else:
            eval = "typeof parent.window.wasdetected !== 'undefined'"
            if await frame.evaluate(eval):
                self.log("Automation detected")
                self.detected = True
