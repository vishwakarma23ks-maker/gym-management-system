document.addEventListener("DOMContentLoaded",()=>{
 const plan=document.getElementById("planSelect"), start=document.getElementById("startDate"), expiry=document.getElementById("expiryDate"), fee=document.getElementById("feeInput");
 function updatePlan(){
  if(!plan||!start||!expiry)return;
  const opt=plan.options[plan.selectedIndex]; if(!opt||!opt.dataset.months)return;
  const d=new Date(start.value+"T12:00:00"); d.setMonth(d.getMonth()+Number(opt.dataset.months));
  const y=d.getFullYear(),m=String(d.getMonth()+1).padStart(2,"0"),day=String(d.getDate()).padStart(2,"0");
  expiry.value=`${y}-${m}-${day}`; if(fee&&!fee.value)fee.value=opt.dataset.price||"";
 }
 if(plan){plan.addEventListener("change",updatePlan);start.addEventListener("change",updatePlan);}
 const canvas=document.getElementById("planChart");
 if(canvas&&window.planLabels){new Chart(canvas,{type:"doughnut",data:{labels:window.planLabels,datasets:[{data:window.planValues,backgroundColor:["#54d68b","#a0e8bd","#263c32","#9aa79f"],borderWidth:0}]},options:{plugins:{legend:{position:"bottom"}},cutout:"68%"}});}
 const rev=document.getElementById("revenueChart");
 if(rev){new Chart(rev,{type:"bar",data:{labels:["Paid revenue"],datasets:[{label:"INR",data:[0],backgroundColor:"#54d68b",borderRadius:8}]},options:{plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,grid:{color:"#edf0ed"}},x:{grid:{display:false}}}}});}
});
