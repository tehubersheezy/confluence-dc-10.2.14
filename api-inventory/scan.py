"""Inventory every JAX-RS endpoint in a Confluence DC install by reading class files.

Runs inside the container (python3 only, no JDK tools needed):
  docker exec -i confluence python3 - < api-inventory/scan.py > api-inventory/endpoints.json

Output: {"endpoints": [...], "models": {java_type: {"fields": {json_name: type}}}}
"""
import glob, io, json, re, struct, sys, zipfile
import xml.etree.ElementTree as ET

WEBINF = "/opt/atlassian/confluence/confluence/WEB-INF"
VERBS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
PRIMS = {"I": "int", "J": "long", "Z": "boolean", "B": "byte", "C": "char", "S": "short", "D": "double", "F": "float", "V": "void"}


# ---------------------------------------------------------------- class files

class Reader:
    def __init__(self, b): self.b, self.i = b, 0
    def u1(self): v = self.b[self.i]; self.i += 1; return v
    def u2(self): v = struct.unpack_from(">H", self.b, self.i)[0]; self.i += 2; return v
    def u4(self): v = struct.unpack_from(">I", self.b, self.i)[0]; self.i += 4; return v
    def take(self, n): v = self.b[self.i:self.i + n]; self.i += n; return v


def parse_class(b):
    r = Reader(b)
    if r.u4() != 0xCAFEBABE: return None
    r.u2(); r.u2()
    n = r.u2(); cp = [None] * n; k = 1
    while k < n:
        t = r.u1()
        if t == 1: cp[k] = r.take(r.u2()).decode("utf-8", "replace")
        elif t in (3, 4): cp[k] = r.u4()
        elif t in (5, 6): r.take(8); k += 1
        elif t in (7, 8, 16, 19, 20): cp[k] = ("ref", r.u2())
        elif t in (9, 10, 11, 12, 17, 18): r.u4()
        elif t == 15: r.take(3)
        else: raise ValueError(t)
        k += 1
    utf = lambda i: cp[i] if isinstance(cp[i], str) else cp[cp[i][1]]

    def elem():
        t = chr(r.u1())
        if t in "BCDFIJSZs":
            v = cp[r.u2()]
            return v if not isinstance(v, tuple) else utf(v[1])
        if t == "e": r.u2(); return utf(r.u2())
        if t == "c": return utf(r.u2())
        if t == "@": return ann()
        if t == "[": return [elem() for _ in range(r.u2())]

    def ann():
        typ = utf(r.u2())[1:-1].replace("/", ".")
        vals = {}
        for _ in range(r.u2()):
            name = utf(r.u2()); vals[name] = elem()
        return {"type": typ, "values": vals}

    def attrs():
        out = {}
        for _ in range(r.u2()):
            name = utf(r.u2()); ln = r.u4(); end = r.i + ln
            if name == "RuntimeVisibleAnnotations":
                out["ann"] = [ann() for _ in range(r.u2())]
            elif name == "RuntimeVisibleParameterAnnotations":
                out["pann"] = [[ann() for _ in range(r.u2())] for _ in range(r.u1())]
            elif name == "Signature":
                out["sig"] = utf(r.u2())
            elif name == "MethodParameters":
                out["pnames"] = []
                for _ in range(r.u1()):
                    ni = r.u2(); r.u2(); out["pnames"].append(utf(ni) if ni else None)
            r.i = end
        return out

    acc = r.u2()
    this = utf(cp[r.u2()][1]); si = r.u2(); sup = utf(cp[si][1]) if si else None
    ifaces = [utf(cp[r.u2()][1]) for _ in range(r.u2())]
    fields = []
    for _ in range(r.u2()):
        facc = r.u2(); name = utf(r.u2()); desc = utf(r.u2())
        fields.append({"acc": facc, "name": name, "desc": desc, **attrs()})
    methods = []
    for _ in range(r.u2()):
        macc = r.u2(); name = utf(r.u2()); desc = utf(r.u2())
        methods.append({"acc": macc, "name": name, "desc": desc, **attrs()})
    dotted = lambda s: s.replace("/", ".") if s else s
    return {"name": dotted(this), "acc": acc, "super": dotted(sup), "ifaces": [dotted(i) for i in ifaces],
            "fields": fields, "methods": methods, **attrs()}


class ClassPool(dict):
    """Plugin-local classes, falling back to WEB-INF/lib classes loaded on demand."""
    lib_index = None

    def __init__(self, local):
        super().__init__(local)
        if ClassPool.lib_index is None:
            ClassPool.lib_index = {}
            for j in glob.glob(WEBINF + "/lib/*.jar"):
                try:
                    for n in zipfile.ZipFile(j).namelist():
                        if n.endswith(".class"):
                            ClassPool.lib_index.setdefault(n[:-6].replace("/", "."), j)
                except Exception:
                    pass
            ClassPool.lib_cache = {}

    def get(self, name, default=None):
        if name in self: return self[name]
        if name in ClassPool.lib_cache: return ClassPool.lib_cache[name]
        j = ClassPool.lib_index.get(name)
        c = None
        if j:
            try: c = parse_class(zipfile.ZipFile(j).read(name.replace(".", "/") + ".class"))
            except Exception: c = None
        ClassPool.lib_cache[name] = c
        return c if c else default


def walk_jar(z, classes):
    for n in z.namelist():
        if n.endswith(".jar"):
            try: walk_jar(zipfile.ZipFile(io.BytesIO(z.read(n))), classes)
            except Exception: pass
        elif n.endswith(".class") and not n.startswith("META-INF/versions"):
            try:
                c = parse_class(z.read(n))
                if c: classes[c["name"]] = c
            except Exception:
                pass


# ---------------------------------------------------------------- type signatures

def parse_sig(s, i=0):
    """Parse one JVM (generic) type signature starting at s[i]; return (pretty, refs, next_i)."""
    c = s[i]
    if c == "[":
        t, refs, i = parse_sig(s, i + 1); return t + "[]", refs, i
    if c in PRIMS: return PRIMS[c], [], i + 1
    if c == "T":
        j = s.index(";", i); return s[i + 1:j], [], j + 1
    if c in "+-":
        return parse_sig(s, i + 1)
    if c == "*": return "?", [], i + 1
    if c == "L":
        j = i + 1; name = ""; args = []; refs = []
        while s[j] not in "<;":
            name += s[j]; j += 1
        if s[j] == "<":
            j += 1
            while s[j] != ">":
                t, r, j = parse_sig(s, j); args.append(t); refs += r
            j += 1
            while s[j] == ".":  # inner class of generic outer
                j += 1
                while s[j] not in "<;": name += "$" + s[j] if False else s[j]; j += 1
                if s[j] == "<":
                    depth = 1; j += 1
                    while depth: depth += {"<": 1, ">": -1}.get(s[j], 0); j += 1
        full = name.replace("/", ".")
        pretty = full.split(".")[-1].replace("$", ".") + (f"<{', '.join(args)}>" if args else "")
        return pretty, [full] + refs, j + 1
    raise ValueError(s[i:])


def method_types(m):
    """Return ([param pretty types], return pretty, refs) using generic Signature when present."""
    s = m.get("sig") or m["desc"]
    if s.startswith("<"):  # strip formal type params
        depth = 0; i = 0
        while True:
            depth += {"<": 1, ">": -1}.get(s[i], 0); i += 1
            if depth == 0: break
        s = s[i:]
    i = s.index("(") + 1; params = []; refs = []
    while s[i] != ")":
        t, r, i = parse_sig(s, i); params.append(t); refs += r
    ret, r, _ = parse_sig(s, i + 1); refs += r
    return params, ret, refs


def erased_params(desc):
    out = []; i = desc.index("(") + 1
    while desc[i] != ")":
        j = i
        while desc[j] == "[": j += 1
        j = desc.index(";", j) + 1 if desc[j] == "L" else j + 1
        t = desc[i:j]; i = j
        out.append(t.lstrip("[")[1:-1].replace("/", ".") if t.lstrip("[").startswith("L") else PRIMS.get(t.lstrip("["), t))
    return out


# ---------------------------------------------------------------- JAX-RS model

def short(t): return t.split(".")[-1]


def jaxrs(anns, kind):
    for a in anns or []:
        if a["type"] in (f"jakarta.ws.rs.{kind}", f"javax.ws.rs.{kind}"):
            return a["values"].get("value", True)
    return None


def is_jaxrs(a): return a["type"].startswith(("jakarta.ws.rs.", "javax.ws.rs."))


def join(*parts):
    p = "/".join(s.strip("/") for s in parts if s and s.strip("/"))
    return "/" + p


def clean_path(p):
    # {id: [0-9]+} -> {id}
    return re.sub(r"\{\s*([^}:\s]+)\s*:[^}]*\}", r"{\1}", p)


def rest_modules(xml):
    mods = []
    try: root = ET.fromstring(xml)
    except ET.ParseError: return mods
    for el in root.iter("rest"):
        version = el.get("version", "")
        base = "/rest" + join(el.get("path", ""))
        if version and version != "none": base = join(base, version)
        pkgs = [p.text.strip() for p in el.findall("package") if p.text]
        if el.get("package"): pkgs.append(el.get("package"))
        mods.append({"key": el.get("key"), "name": el.get("name"), "base": base, "packages": pkgs})
    return mods


def plugin_meta(xml):
    try: root = ET.fromstring(xml)
    except ET.ParseError: return {}
    return {"key": root.get("key"), "name": root.get("name")}


def supers(c):
    return ([c["super"]] if c["super"] else []) + c["ifaces"]


def find_method(classes, cname, name, desc, seen=None):
    """Nearest declaration (self, superclasses, interfaces) carrying JAX-RS annotations."""
    seen = seen if seen is not None else set()
    c = classes.get(cname)
    if not c or cname in seen: return None
    seen.add(cname)
    for m in c["methods"]:
        if m["name"] == name and m["desc"] == desc and any(is_jaxrs(a) for a in m.get("ann", [])):
            return m
    for parent in supers(c):
        hit = find_method(classes, parent, name, desc, seen)
        if hit: return hit
    return None


def all_methods(classes, cname, seen=None):
    seen = seen if seen is not None else set(); out = {}
    c = classes.get(cname)
    if not c or cname in seen: return out
    seen.add(cname)
    for parent in supers(c):
        out.update(all_methods(classes, parent, seen))
    for m in c["methods"]:
        if m["acc"] & 0x0001 and not m["acc"] & 0x1040:  # public, not synthetic/bridge
            out[(m["name"], m["desc"])] = m
    return out


def class_anns(classes, cname):
    c = classes.get(cname); anns = list(c.get("ann", [])) if c else []
    while c and jaxrs(anns, "Path") is None and c["super"]:
        c = classes.get(c["super"]); anns += c.get("ann", []) if c else []
    return anns


def swagger_doc(anns):
    for a in anns:
        if a["type"] == "io.swagger.v3.oas.annotations.Operation":
            v = a["values"]
            return {k: v[k] for k in ("summary", "description", "operationId") if v.get(k)}
    return {}


def endpoints_for(classes, cname, prefix, cls_anns, refs, depth=0):
    out = []
    if depth > 4: return out
    for (name, desc), m in all_methods(classes, cname).items():
        decl = find_method(classes, cname, name, desc) or m
        anns = decl.get("ann", [])
        verb = next((short(a["type"]) for a in anns if is_jaxrs(a) and short(a["type"]) in VERBS), None)
        path = jaxrs(anns, "Path")
        if not verb and path is None: continue
        erased = erased_params(desc)
        try:
            ptypes, ret, trefs = method_types(decl if decl.get("sig") else m)
            if len(ptypes) != len(erased): raise ValueError
        except Exception:
            ptypes, trefs = [short(t) for t in erased], []
            ret = short(desc[desc.index(")") + 1:].strip("L;").replace("/", "."))
        params, body, body_refs = [], None, []
        pann = decl.get("pann") or []
        offset = len(erased) - len(pann)
        pnames = decl.get("pnames") or m.get("pnames") or []
        for i, t in enumerate(erased):
            pa = pann[i - offset] if 0 <= i - offset < len(pann) else []
            kinds = {short(a["type"]): a["values"].get("value") for a in pa}
            src = next((k for k in ("PathParam", "QueryParam", "FormParam", "HeaderParam", "CookieParam", "MatrixParam", "BeanParam", "FormDataParam") if k in kinds), None)
            if "Context" in kinds or "Suspended" in kinds: continue
            if not src and pa and all(a["type"].startswith("com.atlassian.graphql.") for a in pa):
                continue  # GraphQL-only argument; JAX-RS never binds it
            if t in ("jakarta.servlet.http.HttpServletRequest", "javax.servlet.http.HttpServletRequest",
                     "jakarta.servlet.http.HttpServletResponse", "javax.servlet.http.HttpServletResponse"):
                continue
            if src:
                params.append({"in": {"FormDataParam": "multipart"}.get(src, src[:-5].lower()), "name": kinds[src],
                               "java_name": pnames[i] if i < len(pnames) else None,
                               "type": ptypes[i], "default": kinds.get("DefaultValue")})
                if src == "BeanParam": refs.add(t)
            else:
                body = ptypes[i]; refs.add(t)
        refs.update(trefs)
        full = clean_path(join(prefix, path or ""))
        other = [a for a in cls_anns + anns if not is_jaxrs(a)]
        if verb:
            out.append({
                "method": verb, "path": full, "class": cname, "java": name,
                "params": params, "body": body, "returns": ret,
                "consumes": jaxrs(anns, "Consumes") or jaxrs(cls_anns, "Consumes"),
                "produces": jaxrs(anns, "Produces") or jaxrs(cls_anns, "Produces"),
                "doc": swagger_doc(anns),
                "deprecated": any(short(a["type"]) in ("Deprecated", "DeprecatedEndpoint") for a in anns),
                "annotations": other,
                "method_annotations": [a["type"] for a in anns if not is_jaxrs(a)],
            })
        else:
            target = desc[desc.index(")") + 1:].strip("L;").replace("/", ".")
            if classes.get(target):  # subresource locator
                out += endpoints_for(classes, target, full, cls_anns + class_anns(classes, target), refs, depth + 1)
    return out


# ---------------------------------------------------------------- models

JSON_NAME = ("com.fasterxml.jackson.annotation.JsonProperty", "org.codehaus.jackson.annotate.JsonProperty",
             "javax.xml.bind.annotation.XmlElement", "jakarta.xml.bind.annotation.XmlElement",
             "javax.xml.bind.annotation.XmlAttribute", "jakarta.xml.bind.annotation.XmlAttribute")
JSON_IGNORE = ("JsonIgnore", "XmlTransient")
SKIP_MODELS = ("java.", "javax.", "jakarta.", "kotlin.", "com.google.", "io.atlassian.fugue", "org.")


def model_fields(classes, name):
    c = classes.get(name)
    if not c: return None
    fields = {}
    chain = []
    while c and len(chain) < 6:
        chain.append(c); c = classes.get(c["super"]) if c["super"] and not c["super"].startswith("java.") else None
    for c in reversed(chain):
        explicit = {}
        for f in c["fields"]:
            if f["acc"] & 0x0008 or f["acc"] & 0x1000: continue  # static / synthetic
            anns = f.get("ann", [])
            if any(short(a["type"]) in JSON_IGNORE for a in anns): continue
            named = next((a for a in anns if a["type"] in JSON_NAME), None)
            jname = (named["values"].get("value") or named["values"].get("name")) if named else None
            try: t = parse_sig(f.get("sig") or f["desc"])[0]
            except Exception: t = "?"
            if named or f["acc"] & 0x0001:
                explicit[jname if jname and jname != "##default" else f["name"]] = t
        if not explicit:
            for m in c["methods"]:
                if not m["acc"] & 0x0001 or m["acc"] & 0x0008 or m["desc"].startswith("()V") or not m["desc"].startswith("()"): continue
                if any(short(a["type"]) in JSON_IGNORE for a in m.get("ann", [])): continue
                g = re.match(r"(get|is)([A-Z]\w*)$", m["name"])
                if not g or m["name"] == "getClass": continue
                named = next((a for a in m.get("ann", []) if a["type"] in JSON_NAME), None)
                jname = named["values"].get("value") if named else None
                prop = jname or g.group(2)[0].lower() + g.group(2)[1:]
                try: explicit[prop] = method_types(m)[1]
                except Exception: explicit[prop] = "?"
        fields.update(explicit)
    return fields


def collect_models(classes, roots, depth=3):
    models = {}; frontier = set(roots)
    for _ in range(depth):
        nxt = set()
        for name in frontier:
            if name in models or name.startswith(SKIP_MODELS): continue
            c = classes.get(name)
            if not c: continue
            f = model_fields(classes, name)
            if not f: continue
            models[name] = {"fields": f}
            for fld in c["fields"]:
                if fld["acc"] & 0x0008: continue
                try: nxt.update(parse_sig(fld.get("sig") or fld["desc"])[1])
                except Exception: pass
        frontier = nxt
    return models


# ---------------------------------------------------------------- main

def main():
    endpoints, models = [], {}
    for j in sorted(glob.glob(WEBINF + "/atlassian-bundled-plugins/*.jar")):
        try: z = zipfile.ZipFile(j)
        except Exception: continue
        if "atlassian-plugin.xml" not in z.namelist(): continue
        xml = z.read("atlassian-plugin.xml")
        mods = rest_modules(xml)
        if not mods: continue
        local = {}; walk_jar(z, local)
        classes = ClassPool(local)
        meta = plugin_meta(xml)
        refs = set()
        for cname, c in local.items():
            if "$" in cname or c["acc"] & 0x0200: continue  # skip inner classes and interfaces
            if jaxrs(c.get("ann"), "Path") is None: continue
            pkg = cname.rsplit(".", 1)[0]
            matched = [m for m in mods if any(pkg == p or pkg.startswith(p + ".") for p in m["packages"])]
            matched = matched or [m for m in mods if not m["packages"]]
            for mod in matched:
                prefix = join(mod["base"], jaxrs(c["ann"], "Path"))
                for e in endpoints_for(classes, cname, prefix, c["ann"], refs):
                    e.update(plugin=meta.get("key"), plugin_name=meta.get("name"), jar=j.split("/")[-1],
                             module=mod["key"], module_base=mod["base"])
                    endpoints.append(e)
        models.update(collect_models(classes, refs))
    json.dump({"endpoints": endpoints, "models": models}, sys.stdout, indent=1, default=str)


main()
