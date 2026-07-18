with open('simulateur-aides.php', 'r') as f:
    content = f.read()

old = """  var rI=document.createElement('input');rI.type='text';rI.inputMode='numeric';
  rI.value=S.rfr>0?fmtNum(S.rfr)+' EUR':'';
  rI.addEventListener('input',function(){
    var brut=rI.value.replace(/[^0-9]/g,'');
    S.rfr=parseInt(brut)||0;
    rI.value=S.rfr>0?fmtNum(S.rfr)+' EUR':'';
    updatePrev();
  });"""

new = """  var rI=document.createElement('input');rI.type='text';rI.inputMode='numeric';
  rI.value=S.rfr>0?fmtNum(S.rfr)+' EUR':'';
  rI.addEventListener('focus',function(){
    rI.value=S.rfr>0?String(S.rfr):'';
  });
  rI.addEventListener('input',function(){
    var brut=rI.value.replace(/[^0-9]/g,'');
    S.rfr=parseInt(brut)||0;
    rI.value=brut;
    updatePrev();
  });
  rI.addEventListener('blur',function(){
    rI.value=S.rfr>0?fmtNum(S.rfr)+' EUR':'';
  });"""

if old in content:
    content = content.replace(old, new, 1)
    print("✅ Patch focus/blur appliqué")
else:
    print("❌ Pattern non trouvé")

with open('simulateur-aides.php', 'w') as f:
    f.write(content)
