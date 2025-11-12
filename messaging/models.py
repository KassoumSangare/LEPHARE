from django.db import models
from uuid import uuid4

# Create your models here.


class ArolitecSMSDispatching(models.Model):
    climsgid = models.UUIDField(
        db_column="climsgid",
        verbose_name="Identifiant défini par le client",
        primary_key=True,
        max_length=40,
    )
    content = models.TextField(
        db_column="content", verbose_name="Contents", max_length=1000
    )
    receiver = models.CharField(
        db_column="receiver", verbose_name="Receiver", max_length=20
    )
    charset = models.CharField(
        db_column="charset",
        verbose_name="Charset",
        max_length=40,
        null=True,
        blank=True,
    )
    time_to_send = models.DateTimeField(
        db_column="timetosend", verbose_name="Time to send", null=True, blank=True
    )
    dispatching_status = models.CharField(
        verbose_name="Dispatching Status",
        db_column="dispatchingstatus",
        max_length=1,
        null=True,
        blank=True,
    )
    dispatching_error = models.CharField(
        db_column="dispatchingerror",
        verbose_name="Dispatching Error",
        max_length=50,
        null=True,
        blank=True,
    )
    date_created = models.DateTimeField(
        verbose_name="Created At", db_column="datecreated", auto_now_add=True
    )
    date_modified = models.DateTimeField(
        verbose_name="Modified At", db_column="datemodified", auto_now=True
    )

    def __str__(self):
        return "Message # {} sent to {}".format(self.climsgid, self.receiver)

    class Meta:
        db_table = "stdarolitecsmsdispatching"
        verbose_name = "AROLITEC SMS Dispatching"
        verbose_name_plural = "AROLITEC SMS Dispatchings"


class ArolitecSMSResponse(models.Model):
    response_id = models.BigAutoField(
        db_column="responseid",
        verbose_name="Client-Generated Response ID",
        primary_key=True,
    )
    success = models.BooleanField(
        db_column="success", verbose_name="Success", default=False
    )
    msgid = models.CharField(
        db_column="msgid",
        verbose_name="Platform-Generated Message ID",
        unique=True,
        max_length=40,
        null=True,
        blank=True,
    )
    receiver = models.CharField(
        db_column="receiver",
        verbose_name="Receiver",
        max_length=20,
        null=True,
        blank=True,
    )
    cost = models.DecimalField(
        db_column="cost",
        verbose_name="Cost",
        max_digits=19,
        decimal_places=4,
        null=True,
        blank=True,
    )
    error = models.CharField(
        db_column="error", verbose_name="Error", max_length=50, null=True, blank=True
    )
    climsgid = models.ForeignKey(
        ArolitecSMSDispatching,
        db_column="climsgid",
        verbose_name="Client-generated ID",
        related_name="responses",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    date_created = models.DateTimeField(
        verbose_name="Created At", db_column="datecreated", auto_now_add=True
    )
    date_modified = models.DateTimeField(
        verbose_name="Modified At", db_column="datemodified", auto_now=True
    )

    def __str__(self):
        if self.msgid:
            return "Response # {} to message {}".format(
                self.msgid, self.climsgid.climsgid
            )
        else:
            return self.response_id

    class Meta:
        db_table = "stdarolitecsmsresponse"
        verbose_name = "AROLITEC SMS Response"
        verbose_name_plural = "AROLITEC SMS Responses"


class ArolitecSMSFeedback(models.Model):
    feedback_id = models.BigAutoField(
        verbose_name="Client-Generated Feedback ID",
        db_column="feedbackid",
        primary_key=True,
    )
    msgid = models.ForeignKey(
        ArolitecSMSResponse,
        to_field="msgid",
        verbose_name="Platform-Generated Message ID",
        db_column="msgid",
        on_delete=models.CASCADE,
    )
    delivery_date = models.DateTimeField(
        verbose_name="Delivery Date", db_column="deliverydate"
    )
    feedback_type = models.CharField(
        verbose_name="Feedback Type", db_column="feedbacktype", max_length=10
    )
    content = models.CharField(
        verbose_name="Feedback Message", db_column="content", max_length=255
    )

    class Meta:
        abstract = True


class ArolitecSMSAck(ArolitecSMSFeedback):
    dlr = models.CharField(
        verbose_name="Code Accusé Reception", db_column="dlr", max_length=3
    )
    climsgid = models.ForeignKey(
        ArolitecSMSDispatching,
        verbose_name="Client-Generated Message ID",
        db_column="climsgid",
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        verbose_name="Statut Message", db_column="status", max_length=3
    )

    def __str__(self):
        return "Ack for message # {}".format(self.msgid)

    class Meta:
        db_table = "stdarolitecsmsack"
        verbose_name = "AROLITEC SMS Ack"
        verbose_name_plural = "AROLITEC SMS Ack"


class ArolitecSMSMo(ArolitecSMSFeedback):
    sender = models.CharField(
        verbose_name="Message Sender", db_column="sender", max_length=20
    )
    receiver = models.CharField(
        verbose_name="Message Recipient", db_column="receiver", max_length=20
    )

    def __str__(self):
        return "Mo for message # {}".format(self.msgid)

    class Meta:
        db_table = "stdarolitecsmsmo"
        verbose_name = "AROLITEC SMS Mo"
        verbose_name_plural = "AROLITEC SMS Mo"
