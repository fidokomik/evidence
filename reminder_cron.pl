#!/usr/bin/perl
# Author: Petr Vileta, 2012
# License: WTFPL - Do What The Fuck You Want To Public License, http://sam.zoy.org/wtfpl/

use strict;
use DBI;
use Net::SMTP;
use MIME::Base64;
open STDERR,">&STDOUT";

my $starttime=time;
our $mailserver='127.0.0.1';
#our $mailserver='ns.zivnosti.cz';

require '../init.pl';
# require '/var/www/cz/stranapiratska/www/ao/init.pl';
our $dbh;
our ($db,$dbhost,$dbport,$dbuser,$dbpw)=connect_db();
$dbh = DBI->connect("DBI:mysql:$db:$dbhost:$dbport",$dbuser,$dbpw) or die "Can't connect: $DBI::errstr\n";
$dbh->do("SET character_set_connection=utf8");
$dbh->do("SET character_set_client=utf8");
$dbh->do("SET character_set_results=utf8");
my $maingroup=get_setup('maingroup','number'); # cislo skupiny 'Celostatni forum' v tabulce 'phpbb_groups'
my ($datum,$castka,$dalsi,$upominka,$name,$fullname,$id,$den,$mes,$rok,$dden,$dmes,$drok,
    $uden,$umes,$urok,$mail,$clenstvi,$cden,$cmes,$crok);
my $errcnt=my $cnt=0;
my $errors=my $msg='';
our $ksgroups=get_setup('ksgroups','string'); # cisla skupin KS
our $kstopks=get_setup('ks_to_pks','text'); # prevodnik cisla KS na cislo PKS
$kstopks=~s/(\d+)=(\d+)[^\d]+/$1=$2 /sg;
my $predem=get_setup('upominka_dnu_predem','number');
my $po=get_setup('upominka_dnu_po','number');
my $prodl=get_setup('upominka_prodleni_po','number');
my $subj1=get_setup('upominka_subject1','string'); # 1.upominka
my $subj2=get_setup('upominka_subject2','string'); # 2.upominka
my $subj3=get_setup('upominka_subject3','string'); # v prodleni
my $text1=get_setup('upominka_text1','text'); # 1.upominka
my $text2=get_setup('upominka_text2','text'); # 2.upominka
my $text3=get_setup('upominka_text3','text'); # v prodleni
my $aomail=get_setup('ao_mail','text'); # mail administrativniho odboru
my $sth=$dbh->prepare("SELECT `pf_datumclprispevku`,`pf_vyseclprispevku`,
  			`pf_dalsiclprispevek`,`pf_datumupominky`,
				`username`,`pf_fullname`,`phpbb_users`.`user_id`,
				`user_email`,`pf_vznikclenstvi`
			FROM `phpbb_user_group`
			LEFT JOIN `phpbb_users`
				ON(`phpbb_users`.`user_id`=`phpbb_user_group`.`user_id`)
			LEFT JOIN `phpbb_profile_fields_data`
				ON(`phpbb_profile_fields_data`.`user_id`=`phpbb_users`.`user_id`)
			WHERE `phpbb_user_group`.`group_id`=?
			ORDER BY 1 desc");
#my $sth1=$dbh->prepare("select date(now()) >= date(date_sub(date_add(?,INTERVAL 1 year),interval ? day)) as podm1,
#		((date(?)*1=0) or (date(?) <= date(?))) as podm2,
#		((date(?)*1 > 0) and (date_add(?,interval 1 month) > date(?))) as podm3,
#		(date(?) > date(?) and DATEDIFF(date(now()),date(?)) >= ? and DATEDIFF(date(now()),date(?)) >= ? and date(?) < date(?)) as podm4");
my $sth1=$dbh->prepare("SET \@dat:=?,\@predem:=?,\@ddat:=?,\@upom:=?,\@po:=?,\@prodl=?");
my $sth1a=$dbh->prepare("select date(now()) >= date(date_sub(date_add(\@dat,INTERVAL 1 year),interval \@predem day)) as podm1,
	((date(\@ddat)*1=0) or (date(\@ddat) <= date(\@dat))) as podm2,
	((date(\@ddat)*1 > 0) and (date_add(\@upom,interval 1 month) > date(\@ddat))) as podm3,
	(date(\@upom) > date(\@dat) and DATEDIFF(date(now()),date(\@ddat)) >= \@po and DATEDIFF(date(now()),date(\@upom)) >= \@po and date(\@upom) < date(\@dat)) as podm4,
	(date(\@upom) > date(\@dat) and DATEDIFF(date(now()),date(\@ddat)) >= \@prodl and DATEDIFF(date(now()),date(\@upom)) >= \@prodl and date(\@upom) < date(\@dat)) as podm5");
my $sth2=$dbh->prepare("update `phpbb_profile_fields_data` set
			`pf_datumupominky`=DATE_FORMAT(NOW(),'%d-%m-%Y')
		where `user_id`=?");

$sth->execute($maingroup) or die $sth->errstr;
$sth->bind_columns(\($datum,$castka,$dalsi,$upominka,$name,$fullname,$id,$mail,$clenstvi));
while ($sth->fetch)
	{
	$datum=~s/\s//g;
	$dalsi=~s/\s//g;
	$clenstvi=~s/\s//g;
	$upominka=~s/\s//g;
	$castka*=1;
	my ($dat,$ddat,$upom);
	if($datum=~m/^(\d{1,2}).(\d{1,2}).(\d{1,4})$/)
		{
		($den,$mes,$rok)=($1,$2,$3);
		$rok+=2000 if($rok < 100 and $rok > 0);
		}
	else
		{
		($den,$mes,$rok)=(0,0,0);
		}
	$dat=sprintf("%04d-%02d-%02d",$rok,$mes,$den);
	if($dalsi=~m/^(\d{1,2}).(\d{1,2}).(\d{1,4})$/)
		{
		($dden,$dmes,$drok)=($1,$2,$3);
		$drok+=2000 if($drok < 100 and $drok > 0);
		}
	else
		{
		($dden,$dmes,$drok)=(0,0,0);
		}
	$ddat=sprintf("%04d-%02d-%02d",$drok,$dmes,$dden);
	if($upominka=~m/^(\d{1,2}).(\d{1,2}).(\d{1,4})$/)
		{
		($uden,$umes,$urok)=($1,$2,$3);
		$urok+=2000 if($urok < 100 and $urok > 0);
		}
	else
		{
		($uden,$umes,$urok)=(0,0,0);
		}
	$upom=sprintf("%04d-%02d-%02d",$urok,$umes,$uden);
	if($clenstvi=~m/^(\d{1,2}).(\d{1,2}).(\d{1,4})$/)
		{
		($cden,$cmes,$crok)=($1,$2,$3);
		$crok+=2000 if($crok < 100 and $crok > 0);
		}
	else
		{
		($cden,$cmes,$crok)=(0,0,0);
		}
	my $clen=sprintf("%04d-%02d-%02d",$crok,$cmes,$cden);
	next if($clen eq '0000-00-00');
	my ($xdat,$xclen)=($dat,$clen);
	$xdat=~s/-//g;
	$xclen=~s/-//g;
	$xclen=substr($xdat,0,4) . substr($xclen,4);
#	$sth1->execute($dat,$predem,$ddat,$ddat,$dat,$ddat,$upom,$ddat,$upom,$dat,$ddat,$po,$upom,$po,$upom,$dat) or die $sth1->errstr;
# upominat jen podle data vzniku clenstvi

#	if($xdat * 1 < $xclen * 1)
#		{
		$xclen=substr($dat,0,4) . substr($clen,4);
		$sth1->execute($xclen,$predem,$ddat,$upom,$po,$prodl) or die $sth1->errstr;
#		}
#	else
#		{
#		$sth1->execute($dat,$predem,$ddat,$upom,$po,$prodl) or die $sth1->errstr;
#		}
	$sth1a->execute() or die $sth1a->errstr;
	my ($p1,$p2,$p3,$p4,$p5)=$sth1a->fetchrow_array();
	$sth1->finish;
	$sth1a->finish;
	if($p5==1)
		{
		# poslat upozorneni o prodleni (po terminu)
		my $ok=1;
		my $text=$text3;
		my $d1;
		if($drok==0)
			{
			$d1=sprintf("%02d.%02d.%04d",$den,$mes,$rok + 1);
			}
		else
			{
			$d1=sprintf("%02d.%02d.%04d",$dden,$dmes,$drok);
			}
		my $d2=sprintf("%02d.%02d.%04d",$uden,$umes,$urok);
		$text=~s/^(.+?)%s(.+?)%s(.+?)%s(.+)$/$1$d1$2$d2$3$castka$4/s;
		remind_pks($aomail,$subj3,$text,$id);
		if($mail)
			{
			majluj('Piráti - administrativní odbor',$aomail,$mail,
			       $subj3,$text);
			$sth2->execute($id) or $ok=0;
			$sth2->finish;
			$cnt++;
			$msg.="$fullname ($name, ID=$id), $mail - prodleni\n";
			unless($ok)
				{
				$errcnt++;
				$errors.="$fullname ($name, ID=$id), $mail - nelze aktualizovat datum prodleni\n";
				}
			}
		else
			{
			$errcnt++;
			$errors.="$fullname ($name, ID=$id) - nemá nastavený mail\n";
			}
		}
	elsif($p4==1)
		{
		# poslat 2. upominku (po terminu)
		my $ok=1;
		if($mail)
			{
			my $text=$text2;
			my $d1;
			if($drok==0)
				{
				$d1=sprintf("%02d.%02d.%04d",$den,$mes,$rok + 1);
				}
			else
				{
				$d1=sprintf("%02d.%02d.%04d",$dden,$dmes,$drok);
				}
			my $d2=sprintf("%02d.%02d.%04d",$uden,$umes,$urok);
			$text=~s/^(.+?)%s(.+?)%s(.+?)%s(.+)$/$1$d1$2$d2$3$castka$4/s;
			majluj('Piráti - administrativní odbor',$aomail,$mail,
			       $subj2,$text);
			$sth2->execute($id) or $ok=0;
			$sth2->finish;
			$cnt++;
			$msg.="$fullname ($name, ID=$id), $mail - upomínka\n";
			unless($ok)
				{
				$errcnt++;
				$errors.="$fullname ($name, ID=$id), $mail - nelze aktualizovat datum 2. upomínky\n";
				}
			}
		else
			{
			$errcnt++;
			$errors.="$fullname ($name, ID=$id) - nemá nastavený mail\n";
			}
		}
	elsif(($p1==1 and !($p2==0 and $p3==1)) or $dat eq '0000-00-00')
		{
		# poslat 1. upominku (pred terminem)
		my $ok=1;
		if($mail)
			{
			my $text=$text1;
			my $d;
			if($drok==0)
				{
				$d=sprintf("%02d.%02d.%04d",$den,$mes,$rok + 1);
				}
			else
				{
				$d=sprintf("%02d.%02d.%04d",$dden,$dmes,$drok);
				}
			$text=~s/^(.+?)%s(.+?)%s(.+)$/$1$d$2$castka$3/s;
			majluj('Piráti - administrativní odbor',$aomail,$mail,
			       $subj1,$text);
			$sth2->execute($id) or $ok=0;
			$sth2->finish;
			$cnt++;
			$msg.="$fullname ($name, ID=$id), $mail - připomenutí\n";
			unless($ok)
				{
				$errcnt++;
				$errors.="$fullname ($name, ID=$id), $mail - nelze aktualizovat datum 1. upomínky\n";
				}
			}
		else
			{
			$errcnt++;
			$errors.="$fullname ($name, ID=$id) - nemá nastavený mail\n";
			}
		}
	}
$sth->finish;
$dbh->disconnect;
my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime($starttime);
$mon++;
$year = 1900 + $year;
$text1="Upomínač zaplacení členských příspěvků - report\nSpuštěno: "
	. sprintf("%02d.%02d.%04d %02d:%02d:%02d",$mday,$mon,$year,$hour,$min,$sec)
	. "\nUkončeno: ";
($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime(time);
$mon++;
$year = 1900 + $year;
$text1.=sprintf("%02d.%02d.%04d %02d:%02d:%02d",$mday,$mon,$year,$hour,$min,$sec)
	. "\nZasláno celkem " . $cnt*1 . " upomínek.\n";
if($msg)
	{
	$text1.="\n$msg\n";
	}
if($errcnt)
	{
	$text1.="\nBěhem provádění se vyskytly tyto chyby:\n$errors";
	}
majluj('Piráti - administrativní odbor',$aomail,$aomail,
       'Upomínač - report',$text1);

sub majluj
{
my ($fromt,$fromm,$to,$subj,$txt)=@_;
my $s = Net::SMTP->new($mailserver);
$s->mail($fromm);
$s->to($to); # Received: ... for [$to];
$s->data();
$s->datasend("Mime-Version: 1.0\n");
my $tx=encode_base64($fromt);
$tx=~s/(\n|\r)$//s;
$s->datasend("From: \"=?UTF-8?B?$tx?=\" <$fromm>\n");
$s->datasend("To: <" . $to . ">\n");
#$s->datasend("Cc: <" . $fromm . ">\n");
$s->datasend("Reply-To: <$fromm>\n");
$tx=encode_base64($subj);
$tx=~s/(\n|\r)$//s;
$s->datasend("Subject: =?UTF-8?B?$tx?=\n");
$s->datasend("X-Priority: 1\n");
$s->datasend("X-MSMail-Priority: High\n");
$s->datasend("X-Mailer: CPS reminder\n");
$s->datasend("Content-Transfer-Encoding: 8bit\n");
$s->datasend("Content-Type: text/plain; charset=\"utf-8\"\n\n");
$s->datasend($txt . "\n");
$s->dataend();
$s->quit;
}

sub remind_pks
{
my ($aomail,$subj,$text,$clen_id)=@_;
my ($ksgroup,$pksgroup,$pksmail);
my $sth5=$dbh->prepare("SELECT `group_id` from `phpbb_user_group`
	WHERE `user_id`=? AND FIND_IN_SET(`group_id`,'$ksgroups')");
$sth5->execute($clen_id) or die $sth5->errstr;
unless($sth5->rows)
	{
	$sth5->finish;
	return;
	}
($ksgroup)=$sth5->fetchrow_array();
if($kstopks=~m/$ksgroup\=(\d+)/)
	{
	$pksgroup=$1;
	}
else
	{
	$sth5->finish;
	return;
	}
$sth5=$dbh->prepare("SELECT `user_email`
		FROM `phpbb_user_group` AS g
		LEFT JOIN `phpbb_users` AS u ON(`u`.`user_id`=`g`.`user_id`)
		WHERE `g`.`group_id`=?");
$sth5->execute($pksgroup) or die $sth5->errstr;
$sth5->bind_columns(\($pksmail));
while ($sth5->fetch)
	{
#	print "$pksmail\n";
	majluj('Piráti - administrativní odbor - na vědomí',$aomail,$pksmail,$subj,$text) if($pksmail);
	}
$sth5->finish;
}
