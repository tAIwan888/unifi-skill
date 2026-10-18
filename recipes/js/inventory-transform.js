const items = $input.all();
if(items.length!==1 || !Array.isArray(items[0]?.json?.data)) throw new Error('Expected exactly one response with data[]');
const response=items[0].json, devices=response.data;
const online=devices.filter(d=>d?.state==='ONLINE').length;
const total=Number.isInteger(response.totalCount) && response.totalCount>=devices.length ? response.totalCount : null;
const offset=Number.isInteger(response.offset)&&response.offset>=0?response.offset:0;
const partial=total===null || offset>0 || offset+devices.length<total;
return [{json:{kind:'REDACTED_INVENTORY_SUMMARY',deviceCountThisPage:devices.length,onlineThisPage:online,nonOnlineThisPage:devices.length-online,totalCountDeclared:total,hasMoreOrUnknownPages:partial,notes:partial?'PARTIAL_OR_UNKNOWN_PAGINATION':'ONE_PAGE_COMPLETE_PER_API_TOTALCOUNT'}}];
