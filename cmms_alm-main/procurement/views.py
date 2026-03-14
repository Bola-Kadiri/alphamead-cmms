from django.http import HttpResponse
from django.shortcuts import render



def request_quotation(request):

    return render(request, 'procurement/request_quotation.html' )

def purchase_order(request):

     return render(request, 'procurement/purchase_order.html' )

def goods_received(request):

    return render(request, 'procurement/goods_received.html' )

def payment_requisition(request):

     return render(request, 'procurement/payment_requisition.html' )

def saving_loss_report(request):

     return render(request, 'procurement/saving_loss_report.html' )

# def transfer_form(request):

#      return render(request, 'procurement/purchase_order.html' )