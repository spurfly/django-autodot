import json
from django import template
from django.template.defaulttags import IfNode, WithNode, ForNode
from django.core.files.base import ContentFile

#avoidable but non-problematic dependency on django-compressor
from compressor.cache import cache
from compressor.conf import settings

OUTPUT_FILE = 'file'
OUTPUT_INLINE = 'inline'

register = template.Library()

class AuodotContextMember(object):
    def __init__(self, name):
        self.name = name
        
    def __getitem__(self, key):
        return self.__getattr__(key)
    
    def __getattr__(self, key):
        return AuodotContextMember("%s.%s" % (self.name, key))
    
    def __str__(self):
        return "{{=%s}}" % self.name

@register.tag(name="autodot")
def autodot(parser, token):
    """
    <% autodot user %> - starts a template for a user object
    <% autodot user inline %> - ditto but script will be put in the html inline
    <% autodot some.variable[path] as user %> - like <% withjs some.variable[path] as user %><% autodot user %>
    <% autodot some.variable[path] as user inline %> - as expected
    """
    args = token.split_contents(None, 1)
    
    if not len(args) in (2, 3, 4, 5):
        raise template.TemplateSyntaxError("%r tag requires one to four arguments." % args[0])
    
    if len(args) in (4, 5):
        if args[2] != "as":
            raise template.TemplateSyntaxError("%r tag with 3 or 4 arguments must be 'a as b'." % args[0])
        withsrc = (args[1], parser.compile_filter(args[1]))
        args = args[:1] + args[4]
    else:
        withsrc = None
        
    model_name = args[1]
    if len(args) == 3:
        mode = args[2]
        if not mode in (OUTPUT_FILE, OUTPUT_INLINE):
            raise template.TemplateSyntaxError("%r's second argument must be '%s' or '%s'." % (args[0], OUTPUT_FILE, OUTPUT_INLINE))
    else:
        mode = OUTPUT_FILE
        
    nodelist = parser.parse(('endautodot',))
    parser.delete_first_token()
    return AutodotNode(nodelist, model_name, mode, withsrc)

class AutodotNode(template.Node):
    extension = "js"
    output_prefix = "autodot"
    
    def __init__(self, nodelist, model_name, mode=OUTPUT_FILE, withsrc=None):
        self.nodelist = nodelist
        self.model_name = model_name
        self.mode = mode
        self.withsrc = withsrc
        self.template = nodelist.render({model_name: AuodotContextMember("it"),
                                         "AS_AUTODOT": True,
                                         })
        self.js = """%s_tmpl = %s;\n""" % (model_name, json.dumps(self.template))
        if self.mode == OUTPUT_FILE:
            self.save_file()
        
    def save_file(self):
        if self.storage.exists(self.new_filepath):
            return False
        self.storage.save(self.new_filepath, ContentFile(self.js))
        return True
    
    @property
    def new_filepath(self):
        filename = "".join([self.hash, self.extension])
        return os.path.join(
            settings.OUTPUT_DIR.strip(os.sep), self.output_prefix, filename)
        
    @property
    def storage(self):
        from compressor.storage import default_storage
        return default_storage
    
    @property
    def hash(self):
        return get_hexdigest(self.template)[:12]
    
    @property
    def script_tag(self):
        if self.mode == OUTPUT_INLINE:
            return render_to_string(self.template_name_inline, {'content': self.js})
        else:
            return render_to_string(self.template_name, {'url': self.storage.url(self.new_filepath)})
            
    
    def render(self, context):
        if context.get("AS_AUTODOT", None):
            model_var = self.withsrc[0] if self.withsrc else self.model_name
            return "{{= %s_tmpl(%s) }}" % (self.model_name, model_var)
        else:
            if self.withsrc:
                val = withsrc[1].resolve(context)
                context.push()
                context[self.name] = val
                output = self.nodelist.render(context)
                context.pop()
            else:
                output = self.nodelist.render(context)
            context[model_name + "_js"] = self.script_tag
            return output
        
        
class JsNode(object):
    def render(self, context):
        if context.get("AS_AUTOROOT", None):
            return self.render_js(context)
        return super(JsNode,self).render(context)
        

@register.tag(name="ifjs")
def do_ifjs(parser, token):
    """
    The ``{% ifjs %}`` tag is like the `{% if %}` tag in django,
    but it also attempts to do the same thing in the javascript template.
    
    Initial version: use at own risk
    """
    thenode = do_if(parser, token)
    thenode.__class__ = IfjsNode
    return thenode

@register.tag(name="withjs")
def do_withjs(parser, token):
    """
    The ``{% withjs %}`` tag is like the `{% with %}` tag in django,
    but it also attempts to do the same thing in the javascript template.
    
    Initial version: use at own risk.
    """
    thenode = do_with(parser, token)
    thenode.__class__ = WithjsNode
    return thenode


#@register.tag(name="forjs")
def do_forjs(parser, token):
    """
    The ``{% forjs %}`` tag is like the `{% for %}` tag in django,
    but it also attempts to do the same thing in the javascript template.
    
    Initial version: use at own risk.
    """
    thenode = do_for(parser, token)
    thenode.__class__ = ForjsNode
    return thenode


class ForjsNode(JsNode, ForNode):
    template = "{{ var %s; for (var i=0; i < %s.length; i++) { %s = %s[i] }}%s{{ }; }}"
    def render_js(self, context):
        seqname = self.var.value.var.var #.TemplateLiteral.FilterExpression.Variable.string - intentionally brittle
        seq = seqname.split(".",1)
        if len(seq) == 2:
            root, branch = seq
            try:
                root = context.get(root)
            except:
                pass
            seq = ".".join((root, branch))
        else:
            try:
                seq = context.get(seq)
            except:
                pass
        assert len(loopvars) == 1
        return self.template.format(loopvars[0], seq, loopvars[0], seq,
                                     self.nodelist_loop.render(context),
                                     )

class WithjsNode(JsNode, WithNode):
    def render_js(self, context):
        return
        seqname = self.var.value.var.var #.TemplateLiteral.FilterExpression.Variable.string - intentionally brittle
        seq = seqname.split(".",1)
        if len(seq) == 2:
            root, branch = seq
            try:
                root = context.get(root)
            except:
                pass
            seq = ".".join((root, branch))
        else:
            try:
                seq = context.get(seq)
            except:
                pass
        assert len(loopvars) == 1
        return "{{ var %s=%s; }}%s{{ }; }}".format(
                                    loopvar[0],seq,loopvar[0],seq,
                                     self.nodelist_loop.render(context),
                                     )

class IfjsNode(JsNode, IfNode):
    def render_js(self, context):
        varname = self.var.value.var.var #.TemplateLiteral.FilterExpression.Variable.string - intentionally brittle
        var = varname.split(".",1)
        if len(var) == 2:
            root, branch = var
            try:
                root = context.get(root)
            except:
                pass
            var = ".".join((root, branch))
        else:
            try:
                var = context.get(var)
            except:
                pass
        if self.nodelist_false: #has else clause
            return "{{ if (%s && !_.isempty(%s)) { }}%s{{ } else { }}%s{{ }; }}".format(var,var,
                                     self.nodelist_true.render(context),
                                     self.nodelist_false.render(context),
                                     )
        else:
            return "{{ if (%s && !_.isempty(%s)) { }}%s{{ }; }}".format(var,var,
                                     self.nodelist_true.render(context),
                                     )