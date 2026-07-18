with open('simulateur-aides.php', 'r') as f:
    content = f.read()

old_original = """  var rI=document.createElement('input');rI.type='number';rI.value=S.rfr;rI.min=0;rI.step=500;
  rI.addEventListener('input',function(){S.rfr=parseInt(rI.value)||0;updatePrev();});"""

new_simple = """  var rI=document.createElement('input');rI.type='text';rI.inputMode='numeric';
  rI.value=S.rfr>0?fmtNum(S.rfr)+' EUR':'';
  rI.addEventListener('input',function(){
    var brut=rI.value.replace(/[^0-9]/g,'');
    S.rfr=parseInt(brut)||0;
    rI.value=S.rfr>0?fmtNum(S.rfr)+' EUR':'';
    updatePrev();
  });"""

if old_original in content:
    content = content.replace(old_original, new_simple, 1)
    print("✅ Patch RFR appliqué")
else:
    print("❌ Pattern non trouvé")

with open('simulateur-aides.php', 'w') as f:
    f.write(content)
